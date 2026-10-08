from datetime import timedelta

import pytest

from apps.bot.links import customer_link, redeem
from apps.notifications.outbox import deliver_pending
from apps.orders.models import Order
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, cancel_order, confirm_sourcing, create_order
from apps.orders.tests.conftest import stock
from apps.payments.services import confirm_payment, fail_payment, refund_payment, start_payment
from apps.sourcing.models import Offer, Supplier

from .conftest import NOW, start_payload

pytestmark = pytest.mark.django_db
CHAT = 555


@pytest.fixture
def linked(bot, customer, settings):
    settings.SITE_URL = "https://sovga.uz"
    redeem(start_payload(customer_link(customer, NOW)), CHAT, NOW)
    customer.refresh_from_db()
    return customer


def order_for(customer) -> Order:
    return create_order(customer, [CartItem("IP16P-256-B", 1)], "card", DeliveryAddress("Ташкент"), "", NOW)


def messages(telegram) -> list[str]:
    deliver_pending(NOW + timedelta(days=365))  # всё, что уже записано, — к отправке
    return telegram.sent(CHAT)


def test_supplier_confirmation_invites_to_pay(linked, telegram, shop):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    stock(shop["phone"], 5, supplier=Supplier.objects.create(name="Опт", connector_type=Supplier.Connector.TELEGRAM))
    order = order_for(linked)

    confirm_sourcing(order, NOW, actor="manager:anna")

    text = messages(telegram)[-1]
    assert order.number in text and "Ждёт оплаты" in text and "30 минут" in text
    assert f"https://sovga.uz/ru/orders/{order.number}" in text


def test_customer_language(linked, telegram, shop):
    linked.language = "uz"
    linked.save()
    order = order_for(linked)

    cancel_order(order, NOW, actor="customer:x", by_customer=True)

    text = messages(telegram)[-1]
    assert "Bekor qilindi" in text and f"/uz/orders/{order.number}" in text


def test_payment_steps_are_quiet_until_paid(linked, telegram, shop):
    order = order_for(linked)

    start_payment(order, NOW, actor="payme")
    fail_payment(order, NOW, actor="payme")
    assert messages(telegram) == []

    start_payment(order, NOW, actor="payme")
    confirm_payment(order, NOW, actor="payme", provider="Payme")

    assert ["Оплачен" in text for text in messages(telegram)] == [True]


def test_refund_says_money_comes_back(linked, telegram, shop):
    order = order_for(linked)
    start_payment(order, NOW, actor="payme")
    confirm_payment(order, NOW, actor="payme", provider="Payme")

    refund_payment(order, NOW, actor="payme")

    assert "вернутся" in messages(telegram)[-1]


def test_cancellation_reason_is_shown(linked, telegram, shop):
    order = order_for(linked)

    cancel_order(order, NOW, actor="manager:anna", note="Повреждена упаковка")

    assert "Повреждена упаковка" in messages(telegram)[-1]


def test_nothing_without_a_linked_chat(bot, telegram, customer, shop):
    cancel_order(order_for(customer), NOW, actor="customer:x", by_customer=True)

    deliver_pending(NOW)
    assert {payload["chat_id"] for method, payload in telegram.calls if method == "sendMessage"} == {"-100"}


def test_courier_details_reach_the_customer(linked, telegram, shop):
    from decimal import Decimal

    from apps.delivery.carriers import Handover
    from apps.inventory.imei import with_check_digit
    from apps.inventory.services import receive_unit
    from apps.orders.fulfilment import add_unit, deliver, ship, start_picking

    device = with_check_digit("35693803560001")
    receive_unit(variant=shop["phone"], warehouse=shop["warehouse"], cost_usd=Decimal("1000"), imei1=device)
    order = order_for(linked)
    start_payment(order, NOW, actor="payme")
    confirm_payment(order, NOW, actor="payme", provider="Payme")
    start_picking(order, NOW, actor="manager:anna")
    add_unit(order.lines.get(), device, NOW, actor="manager:anna", uzimei_registered=True)

    ship(order, "own", Handover(courier_name="Азиз", courier_phone="901234567"), NOW, actor="manager:anna")
    assert "Курьер: Азиз, +998901234567" in messages(telegram)[-1]

    deliver(order, NOW, actor="manager:anna")
    assert "Доставлен" in messages(telegram)[-1]


def test_return_messages(linked, telegram, shop, settings):
    from datetime import timedelta
    from decimal import Decimal

    from apps.delivery.carriers import Handover
    from apps.inventory.imei import with_check_digit
    from apps.inventory.services import receive_unit
    from apps.orders.fulfilment import add_unit, deliver, ship, start_picking
    from apps.orders.returns import complete_delivered, inspect_return, open_return, refund_return

    settings.RETURN_DAYS = 10
    devices = [with_check_digit(f"3569380356000{n}") for n in (1, 2)]
    for device in devices:
        receive_unit(variant=shop["phone"], warehouse=shop["warehouse"], cost_usd=Decimal("1000"), imei1=device)
    first, second = order_for(linked), order_for(linked)
    for order, device in ((first, devices[0]), (second, devices[1])):
        start_payment(order, NOW, actor="payme")
        confirm_payment(order, NOW, actor="payme", provider="Payme")
        start_picking(order, NOW, actor="manager:anna")
        add_unit(order.lines.get(), device, NOW, actor="manager:anna", uzimei_registered=True)
        ship(order, "own", Handover(courier_name="Азиз", courier_phone="901234567"), NOW, actor="manager:anna")
        deliver(order, NOW, actor="manager:anna")
    messages(telegram)
    sent_before = len(telegram.sent(CHAT))

    assert complete_delivered(NOW + timedelta(days=11)) == 2
    assert len(messages(telegram)) == sent_before  # «Завершён» по сроку — без сообщения

    first.refresh_from_db()
    open_return(first, "Не подошёл", NOW + timedelta(days=1), actor="manager:anna")
    assert "Причина: Не подошёл" in messages(telegram)[-1]
    inspect_return(first, [devices[0]], gift_returned=True, now=NOW, actor="manager:anna")
    assert "К возврату 14 080 000 сум" in messages(telegram)[-1]
    refund_return(first, NOW, actor="manager:anna")
    assert "Деньги возвращены: 14 080 000 сум" in messages(telegram)[-1]
