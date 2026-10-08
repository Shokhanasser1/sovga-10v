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
    deliver_pending(NOW)
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
