from datetime import timedelta

import pytest

from apps.notifications.models import OutboxEvent
from apps.orders.models import Order
from apps.orders.services import OrderError
from apps.payments.services import (
    PAYMENT_WINDOW,
    PICKING_HOLD,
    confirm_payment,
    fail_payment,
    refund_payment,
    start_payment,
)
from apps.sourcing.models import Reservation

from .conftest import NOW

pytestmark = pytest.mark.django_db
S = Order.Status
LATER = NOW + timedelta(minutes=5)


def reservations(order):
    return Reservation.objects.filter(ref=order.number)


def test_start_payment_opens_the_payment_window(order):
    start_payment(order, LATER, actor="payme")

    order.refresh_from_db()
    assert order.status == S.AWAITING_PAYMENT
    assert order.price_lock_until == LATER + PAYMENT_WINDOW
    assert {r.expires_at for r in reservations(order)} == {LATER + PAYMENT_WINDOW}


def test_start_payment_twice_keeps_the_status(order):
    start_payment(order, LATER, actor="payme")

    start_payment(order, LATER, actor="payme")

    order.refresh_from_db()
    assert order.status == S.AWAITING_PAYMENT
    assert order.events.filter(status_to=S.AWAITING_PAYMENT).count() == 1


def test_cancelled_order_cannot_be_paid(order):
    Order.objects.filter(pk=order.pk).update(status=S.CANCELLED)

    with pytest.raises(OrderError):
        start_payment(order, LATER, actor="payme")


def test_confirm_payment_marks_paid_and_holds_stock_until_picking(order):
    start_payment(order, LATER, actor="payme")

    confirm_payment(order, LATER, actor="payme", provider="Payme")

    order.refresh_from_db()
    assert order.status == S.PAID
    assert {r.expires_at for r in reservations(order)} == {LATER + PICKING_HOLD}
    event = OutboxEvent.objects.get(type="order.paid")
    assert event.payload == {"number": order.number, "total": order.total_uzs, "provider": "Payme"}


def test_payment_must_be_started_first(order):
    with pytest.raises(OrderError):
        confirm_payment(order, LATER, actor="payme", provider="Payme")


def test_failed_payment_lets_the_customer_try_again(order):
    start_payment(order, LATER, actor="click")

    fail_payment(order, LATER, actor="click")

    order.refresh_from_db()
    assert order.status == S.CONFIRMED
    assert order.price_lock_until == LATER + timedelta(minutes=30)


def test_refund_after_payment_cancels_the_order(order):
    start_payment(order, LATER, actor="payme")
    confirm_payment(order, LATER, actor="payme", provider="Payme")

    refund_payment(order, LATER, actor="payme")

    order.refresh_from_db()
    assert order.status == S.CANCELLED
    assert not reservations(order).filter(released_at__isnull=True).exists()


def test_no_refund_once_the_courier_has_it(order):
    Order.objects.filter(pk=order.pk).update(status=S.HANDED_TO_CARRIER)

    with pytest.raises(OrderError):
        refund_payment(order, LATER, actor="payme")
