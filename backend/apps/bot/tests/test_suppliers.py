from datetime import timedelta
from decimal import Decimal

import pytest

from apps.bot.dispatch import handle_update
from apps.notifications.outbox import deliver_pending
from apps.orders.models import Order, OrderEvent, SupplierRequest
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, cancel_order, create_order
from apps.orders.supplier_requests import alert_silent_requests
from apps.orders.tests.conftest import stock
from apps.sourcing.models import Offer, Supplier, SupplierSkuMap

from .conftest import NOW, message

pytestmark = pytest.mark.django_db
S = Order.Status
R = SupplierRequest.Status
SUPPLIER_CHAT = 777
MANAGERS = "-100"


@pytest.fixture
def supplier(shop):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    supplier = Supplier.objects.create(name="Опт Чиланзар", connector_type=Supplier.Connector.TELEGRAM,
                                       telegram_chat_id=SUPPLIER_CHAT)
    stock(shop["phone"], 5, supplier=supplier)
    SupplierSkuMap.objects.create(supplier=supplier, supplier_code="APL-16P-256", variant=shop["phone"])
    return supplier


@pytest.fixture
def order(bot, telegram, supplier, customer):
    order = create_order(customer, [CartItem("IP16P-256-B", 1, gift_sku="CASE-1")], "card", DeliveryAddress("Ташкент"), "", NOW)
    deliver_pending(NOW)
    return order


def press(request: SupplierRequest, choice: str, chat_id: int = SUPPLIER_CHAT, data: str | None = None) -> None:
    query = {
        "id": "cb-1", "from": {"id": chat_id}, "data": data or f"sr:{request.pk}:{choice}",
        "message": {"message_id": request.message_id or 1, "chat": {"id": chat_id}, "text": "Заказ"},
    }
    handle_update({"update_id": 1, "callback_query": query}, NOW)


def say(text: str, chat_id: int = SUPPLIER_CHAT) -> None:
    handle_update(message(chat_id, text), NOW)


def test_supplier_gets_the_order_with_buttons(order, telegram):
    request = SupplierRequest.objects.get(order=order)
    sent = [payload for method, payload in telegram.calls if method == "sendMessage" and payload["chat_id"] == SUPPLIER_CHAT][-1]

    assert order.number in sent["text"] and "iPhone 16 Pro" in sent["text"] and "× 1" in sent["text"]
    assert "$1000.00" in sent["text"] and "APL-16P-256" in sent["text"]
    assert "Чехол" not in sent["text"]  # подарок с нашего склада поставщика не касается
    buttons = [b["callback_data"] for row in sent["reply_markup"]["inline_keyboard"] for b in row]
    assert buttons == [f"sr:{request.pk}:yes", f"sr:{request.pk}:no", f"sr:{request.pk}:price"]
    assert request.sent_at is not None and request.message_id


def test_yes_confirms_the_order(order, telegram):
    request = SupplierRequest.objects.get(order=order)

    press(request, "yes")

    order.refresh_from_db()
    assert order.status == S.CONFIRMED
    assert order.price_lock_until > NOW
    assert "подтверждён" in telegram.last("answerCallbackQuery")["text"]
    assert "✅" in telegram.last("editMessageText")["text"]


def test_no_cancels_and_zeroes_the_offer(order, telegram, supplier):
    press(SupplierRequest.objects.get(order=order), "no")

    order.refresh_from_db()
    assert order.status == S.CANCELLED
    assert Offer.objects.get(supplier=supplier).qty_available == 0
    deliver_pending(NOW + timedelta(seconds=1))
    assert any("нет в наличии" in text for text in telegram.sent(MANAGERS))


def test_other_price_goes_to_the_manager(order, telegram):
    request = SupplierRequest.objects.get(order=order)
    press(request, "price")
    assert "цену в долларах" in telegram.sent(SUPPLIER_CHAT)[-1]

    say("дорого")
    say("٩٨٥")  # цифры не ASCII — не принимаем
    assert "числом" in telegram.sent(SUPPLIER_CHAT)[-1]

    say("985,50")

    request.refresh_from_db()
    assert (request.status, request.proposed_cost_usd) == (R.PRICE_OFFERED, Decimal("985.50"))
    order.refresh_from_db()
    assert order.status == S.SOURCING
    deliver_pending(NOW + timedelta(seconds=1))
    alert = telegram.sent(MANAGERS)[-1]
    assert "$985.50" in alert and "$1000.00" in alert


def test_supplier_can_change_mind_after_price_button(order):
    request = SupplierRequest.objects.get(order=order)
    press(request, "price")

    press(request, "yes")

    order.refresh_from_db()
    assert order.status == S.CONFIRMED


def test_a_foreign_chat_cannot_answer(order, telegram):
    press(SupplierRequest.objects.get(order=order), "yes", chat_id=888)

    order.refresh_from_db()
    assert order.status == S.SOURCING
    assert telegram.last("answerCallbackQuery")["show_alert"] is True


@pytest.mark.parametrize("data", ["sr:abc:yes", "zz", "sr:999999:yes", "sr:1:maybe", ""])
def test_broken_buttons(order, telegram, data):
    press(SupplierRequest.objects.get(order=order), "", data=data)

    order.refresh_from_db()
    assert order.status == S.SOURCING
    assert telegram.last("answerCallbackQuery")["text"]


def test_answer_after_the_order_was_cancelled(order, telegram):
    cancel_order(order, NOW, actor="customer:x", by_customer=True)

    press(SupplierRequest.objects.get(order=order), "yes")

    order.refresh_from_db()
    assert order.status == S.CANCELLED
    assert "уже есть ответ" in telegram.last("answerCallbackQuery")["text"]


def test_second_press_changes_nothing(order):
    request = SupplierRequest.objects.get(order=order)

    press(request, "yes")
    press(request, "no")

    order.refresh_from_db()
    assert order.status == S.CONFIRMED
    assert OrderEvent.objects.filter(order=order, status_to=S.CONFIRMED).count() == 1


def test_every_supplier_of_the_order_must_confirm(bot, telegram, supplier, customer, shop):
    other = shop["supplier"]  # «Чехлы оптом», прайс-таблица — тоже нужно подтверждение
    other.telegram_chat_id = 778
    other.save()
    order = create_order(
        customer, [CartItem("IP16P-256-B", 1), CartItem("CASE-REMOTE", 1)], "card", DeliveryAddress("Ташкент"), "", NOW
    )
    deliver_pending(NOW)
    phone_request = SupplierRequest.objects.get(order=order, supplier=supplier)
    case_request = SupplierRequest.objects.get(order=order, supplier=other)

    press(phone_request, "yes")
    order.refresh_from_db()
    assert order.status == S.SOURCING

    press(case_request, "yes", chat_id=778)
    order.refresh_from_db()
    assert order.status == S.CONFIRMED


def test_supplier_without_bot_is_confirmed_by_a_manager(bot, telegram, supplier, customer):
    supplier.telegram_chat_id = None
    supplier.save()

    order = create_order(customer, [CartItem("IP16P-256-B", 1)], "card", DeliveryAddress("Ташкент"), "", NOW)
    deliver_pending(NOW)

    assert telegram.sent(SUPPLIER_CHAT) == []
    assert any(order.number in text and "вручную" in text for text in telegram.sent(MANAGERS))


def test_silent_supplier_is_reported_once(order, telegram):
    sent_at = SupplierRequest.objects.get(order=order).sent_at

    assert alert_silent_requests(sent_at + timedelta(minutes=29)) == 0
    assert alert_silent_requests(sent_at + timedelta(minutes=31)) == 1
    assert alert_silent_requests(sent_at + timedelta(minutes=50)) == 0

    deliver_pending(sent_at + timedelta(minutes=32))
    assert any("молчит" in text for text in telegram.sent(MANAGERS))


@pytest.fixture
def picking(order, telegram):
    from apps.orders.fulfilment import start_picking
    from apps.payments.services import confirm_payment, start_payment

    press(SupplierRequest.objects.get(order=order), "yes")
    start_payment(order, NOW, actor="payme")
    confirm_payment(order, NOW, actor="payme", provider="Payme")
    start_picking(order, NOW, actor="manager:anna")
    deliver_pending(NOW + timedelta(seconds=1))
    return order


def device(n: int) -> str:
    from apps.inventory.imei import with_check_digit

    return with_check_digit(f"3569380356{n:04d}")


def test_supplier_is_asked_for_imei_when_picking_starts(picking, telegram):
    text = telegram.sent(SUPPLIER_CHAT)[-1]

    assert picking.number in text and "IMEI" in text and "iPhone 16 Pro" in text


def test_supplier_sends_imei(picking, telegram):
    from apps.inventory.models import InventoryUnit

    say(device(1))

    unit = InventoryUnit.objects.get(imei1=device(1))
    assert unit.order_line.order == picking and unit.received_for_order
    reply = telegram.sent(SUPPLIER_CHAT)[-1]
    assert "Записали" in reply and picking.number in reply and "всё" in reply

    say(device(2))
    assert "не нужен" in telegram.sent(SUPPLIER_CHAT)[-1]


def test_supplier_imei_with_order_number(picking, telegram):
    say(f"SG999999 {device(1)}")
    assert "не нужен" in telegram.sent(SUPPLIER_CHAT)[-1]

    say(f"{picking.number} {device(1)}")
    assert "Записали" in telegram.sent(SUPPLIER_CHAT)[-1]


def test_bad_supplier_imei(picking, telegram):
    say("356938035600009")  # контрольная цифра не сходится

    assert "Неверный IMEI" in telegram.sent(SUPPLIER_CHAT)[-1]


def test_imei_from_a_stranger_is_ignored(picking, telegram):
    from apps.inventory.models import InventoryUnit

    say(device(1), chat_id=999)

    assert not InventoryUnit.objects.exists()
    assert "/orders" in telegram.sent(999)[-1]
