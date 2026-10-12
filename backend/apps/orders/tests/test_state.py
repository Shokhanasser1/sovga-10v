import pytest

from apps.orders.models import Order
from apps.orders.state import CANCELLABLE, CUSTOMER_CANCELLABLE, FINAL, TRANSITIONS, can_transition

S = Order.Status


def test_every_status_is_described():
    assert set(TRANSITIONS) == set(S.values)


@pytest.mark.parametrize(
    "current, target",
    [
        (S.SOURCING, S.CONFIRMED),
        (S.CONFIRMED, S.AWAITING_PAYMENT),
        (S.AWAITING_PAYMENT, S.PAID),
        (S.AWAITING_PAYMENT, S.CONFIRMED),  # оплата не прошла — можно попробовать снова
        (S.PAID, S.PICKING),
        (S.PICKING, S.HANDED_TO_CARRIER),
        (S.HANDED_TO_CARRIER, S.DELIVERED),
        (S.DELIVERED, S.COMPLETED),
        (S.DELIVERED, S.RETURN_REQUESTED),
        (S.RETURN_REQUESTED, S.INSPECTED),
        (S.INSPECTED, S.REFUNDED),
    ],
)
def test_allowed_transitions(current, target):
    assert can_transition(current, target)


@pytest.mark.parametrize(
    "current, target",
    [
        (S.SOURCING, S.PAID),  # нельзя оплатить, пока поставщик не подтвердил
        (S.CONFIRMED, S.PICKING),  # нельзя собирать неоплаченное
        (S.HANDED_TO_CARRIER, S.CANCELLED),  # после отгрузки — только возврат
        (S.CANCELLED, S.CONFIRMED),
        (S.PAID, S.PAID),
    ],
)
def test_forbidden_transitions(current, target):
    assert not can_transition(current, target)


def test_cancel_only_before_shipping():
    assert CANCELLABLE == {
        S.SOURCING, S.CONFIRMED, S.AWAITING_PAYMENT, S.INSTALLMENT_PENDING,
        S.PAID, S.SIGNED, S.COD, S.PICKING,
    }
    assert all(can_transition(status, S.CANCELLED) for status in CANCELLABLE)


def test_customer_cancels_only_unpaid_orders():
    # Оплата при получении — тоже не оплачен: покупатель отменяет сам, пока не начали сборку.
    assert CUSTOMER_CANCELLABLE == {S.SOURCING, S.CONFIRMED, S.AWAITING_PAYMENT, S.COD}


def test_final_statuses_have_no_exits():
    assert FINAL == {S.CANCELLED, S.REFUNDED}
    assert all(not TRANSITIONS[status] for status in FINAL)
