from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.customers.services import customer_for_phone
from apps.notifications.models import OutboxEvent
from apps.orders.models import Order, OrderLine
from apps.orders.quote import CartItem
from apps.orders.services import (
    PRICE_LOCK,
    SOURCING_SLA,
    DeliveryAddress,
    OrderError,
    cancel_order,
    confirm_sourcing,
    create_order,
    expire_orders,
    transition,
)
from apps.sourcing.models import Offer, Reservation, Supplier

from .conftest import stock

pytestmark = pytest.mark.django_db

NOW = timezone.now()
PHONE_SKU = "IP16P-256-B"
ADDRESS = DeliveryAddress("Ташкент, Юнусабад 4-12", "напротив школы №110")


@pytest.fixture
def customer():
    return customer_for_phone("+998901234567")


def order_for(customer, *items, now=NOW):
    return create_order(customer, list(items), "card", ADDRESS, "", now)


def move_phone_to_supplier(shop, connector):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    supplier = Supplier.objects.create(name=f"Поставщик {connector}", connector_type=connector)
    stock(shop["phone"], 5, supplier=supplier)


def test_own_stock_order_is_ready_for_payment(shop, customer):
    order = order_for(customer, CartItem(PHONE_SKU, 1, gift_sku="CASE-1"))

    assert order.status == Order.Status.CONFIRMED
    assert order.number == f"SG{order.pk:06d}"
    assert order.total_uzs == 14_080_000
    assert order.price_lock_until == NOW + PRICE_LOCK
    main, gift = order.lines.all()
    assert (main.variant.sku, main.price_uzs, main.is_gift) == (PHONE_SKU, 14_080_000, False)
    assert (gift.variant.sku, gift.price_uzs, gift.is_gift, gift.gift_for) == ("CASE-1", 0, True, main)
    reservations = Reservation.objects.filter(ref=order.number)
    assert reservations.count() == 2
    assert {r.expires_at for r in reservations} == {order.price_lock_until}
    assert order.events.get().status_to == Order.Status.CONFIRMED
    event = OutboxEvent.objects.get(type="order.created")
    assert event.payload["number"] == order.number


def test_supplier_without_api_must_confirm_first(shop, customer):
    move_phone_to_supplier(shop, Supplier.Connector.TELEGRAM)

    order = order_for(customer, CartItem(PHONE_SKU, 1))

    assert order.status == Order.Status.SOURCING
    assert order.sla_deadline == NOW + SOURCING_SLA
    assert Reservation.objects.get(ref=order.number).is_soft


def test_supplier_with_api_is_trusted(shop, customer):
    move_phone_to_supplier(shop, Supplier.Connector.API)

    assert order_for(customer, CartItem(PHONE_SKU, 1)).status == Order.Status.CONFIRMED


def test_invalid_cart_creates_nothing(shop, customer):
    with pytest.raises(OrderError) as exc:
        order_for(customer, CartItem(PHONE_SKU, 1, gift_sku="CASE-PREMIUM"))

    assert "подарок" in exc.value.message
    assert not Order.objects.exists()
    assert not Reservation.objects.exists()


def test_stock_taken_meanwhile_rolls_back_everything(shop, customer, monkeypatch):
    calls = []

    def reserve_then_run_out(variant, qty, ref, now, ttl):
        calls.append(variant.sku)
        if variant.sku == "CASE-1":
            return None
        from apps.sourcing.reservations import reserve

        return reserve(variant, qty, ref, now, ttl)

    monkeypatch.setattr("apps.orders.services.reserve", reserve_then_run_out)

    with pytest.raises(OrderError):
        order_for(customer, CartItem(PHONE_SKU, 1, gift_sku="CASE-1"))

    assert calls == [PHONE_SKU, "CASE-1"]
    assert not Order.objects.exists()
    assert not OrderLine.objects.exists()
    assert not Reservation.objects.exists()


def test_cancel_releases_reservations(shop, customer):
    order = order_for(customer, CartItem(PHONE_SKU, 1, gift_sku="CASE-1"))

    cancel_order(order, NOW, actor="customer", by_customer=True)

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert not Reservation.objects.filter(ref=order.number, released_at__isnull=True).exists()
    assert [e.status_to for e in order.events.all()] == [Order.Status.CONFIRMED, Order.Status.CANCELLED]


def test_customer_cannot_cancel_a_paid_order(shop, customer):
    order = order_for(customer, CartItem(PHONE_SKU, 1))
    Order.objects.filter(pk=order.pk).update(status=Order.Status.PAID)
    order.refresh_from_db()

    with pytest.raises(OrderError):
        cancel_order(order, NOW, actor="customer", by_customer=True)


def test_forbidden_transition(shop, customer):
    order = order_for(customer, CartItem(PHONE_SKU, 1))

    with pytest.raises(OrderError):
        transition(order, Order.Status.DELIVERED, NOW, actor="manager:anna")


def test_supplier_confirmation_starts_the_payment_window(shop, customer):
    move_phone_to_supplier(shop, Supplier.Connector.TELEGRAM)
    order = order_for(customer, CartItem(PHONE_SKU, 1))
    later = NOW + timedelta(minutes=40)

    confirm_sourcing(order, later, actor="manager:anna")

    order.refresh_from_db()
    assert order.status == Order.Status.CONFIRMED
    assert order.price_lock_until == later + PRICE_LOCK
    assert Reservation.objects.get(ref=order.number).expires_at == later + PRICE_LOCK


def test_expired_orders_are_cancelled(shop, customer):
    unpaid = order_for(customer, CartItem(PHONE_SKU, 1))
    fresh = order_for(customer, CartItem("CASE-1", 1), now=NOW + timedelta(minutes=25))

    assert expire_orders(NOW + PRICE_LOCK + timedelta(seconds=1)) == 1

    unpaid.refresh_from_db()
    fresh.refresh_from_db()
    assert unpaid.status == Order.Status.CANCELLED
    assert fresh.status == Order.Status.CONFIRMED


def test_silent_supplier_cancels_the_order(shop, customer):
    move_phone_to_supplier(shop, Supplier.Connector.TELEGRAM)
    order = order_for(customer, CartItem(PHONE_SKU, 1))

    assert expire_orders(NOW + SOURCING_SLA + timedelta(seconds=1)) == 1
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert "поставщик" in order.events.last().note.lower()


def test_new_order_notifies_managers(shop, customer, monkeypatch):
    from apps.notifications.outbox import deliver_pending

    sent = []
    monkeypatch.setattr("apps.orders.handlers.notify_managers", sent.append)
    order = order_for(customer, CartItem(PHONE_SKU, 1, gift_sku="CASE-1"))

    deliver_pending(NOW)

    assert order.number in sent[0]
    assert "14 080 000" in sent[0]
    assert "Чехол case" in sent[0]


def test_order_rate_is_recorded(shop, customer):
    assert order_for(customer, CartItem(PHONE_SKU, 1)).rate == Decimal("12800")


def test_run_jobs_cancels_expired_orders_and_delivers_events(shop, customer, monkeypatch):
    from io import StringIO

    import requests
    from django.core.management import call_command

    def cbu_down(day):
        raise requests.ConnectionError("cbu.uz недоступен")

    sent = []
    monkeypatch.setattr("apps.pricing.management.commands.fetch_cbu_rate.fetch_usd_rate", cbu_down)
    monkeypatch.setattr("apps.orders.handlers.notify_managers", sent.append)
    monkeypatch.setattr("apps.core.management.commands.run_jobs.timezone.now", lambda: NOW + PRICE_LOCK * 2)
    order = order_for(customer, CartItem(PHONE_SKU, 1))

    call_command("run_jobs", stdout=StringIO(), stderr=StringIO())

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert sent and order.number in sent[0]
    assert OutboxEvent.objects.get(type="order.created").status == OutboxEvent.Status.DONE


def test_customer_cancel_rechecks_the_status_under_lock(shop, customer):
    """Оплата пришла между загрузкой заказа и отменой — устаревший объект не даёт отменить оплаченное."""
    stale = order_for(customer, CartItem(PHONE_SKU, 1))
    Order.objects.filter(pk=stale.pk).update(status=Order.Status.PAID)

    with pytest.raises(OrderError):
        cancel_order(stale, NOW, actor="customer", by_customer=True)

    assert Order.objects.get(pk=stale.pk).status == Order.Status.PAID
    assert Reservation.objects.filter(ref=stale.number, released_at__isnull=True).exists()


def test_supplier_confirmation_does_not_rewind_a_started_payment(shop, customer):
    move_phone_to_supplier(shop, Supplier.Connector.TELEGRAM)
    order = order_for(customer, CartItem(PHONE_SKU, 1))
    confirm_sourcing(order, NOW, actor="manager:anna")
    Order.objects.filter(pk=order.pk).update(status=Order.Status.AWAITING_PAYMENT)

    with pytest.raises(OrderError):
        confirm_sourcing(order, NOW, actor="manager:anna")
    order.refresh_from_db()
    assert order.status == Order.Status.AWAITING_PAYMENT


def test_order_remembers_the_address_for_next_time(shop, customer):
    from django.test import Client

    from apps.customers.models import Address

    client = Client()
    client.force_login(customer.user)
    assert client.get("/api/v1/auth/me/").json()["customer"]["address"] is None

    order_for(customer, CartItem(PHONE_SKU, 1))
    create_order(customer, [CartItem(PHONE_SKU, 1)], "card", DeliveryAddress("Ташкент, Юнусабад 4-12", "у школы"), "", NOW)

    assert Address.objects.filter(customer=customer).count() == 2
    assert client.get("/api/v1/auth/me/").json()["customer"]["address"] == {
        "text": "Ташкент, Юнусабад 4-12", "landmark": "у школы",
    }
    create_order(customer, [CartItem(PHONE_SKU, 1)], "card", DeliveryAddress("Ташкент, Юнусабад 4-12", "у школы"), "", NOW)
    assert Address.objects.filter(customer=customer).count() == 2
