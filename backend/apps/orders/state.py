"""Машина состояний заказа (спецификация, раздел 5). Любая смена статуса — только по этой таблице."""

from .models import Order

S = Order.Status

TRANSITIONS: dict[str, set[str]] = {
    S.SOURCING: {S.CONFIRMED, S.CANCELLED},
    S.CONFIRMED: {S.AWAITING_PAYMENT, S.INSTALLMENT_PENDING, S.COD, S.CANCELLED},
    S.AWAITING_PAYMENT: {S.PAID, S.CONFIRMED, S.CANCELLED},
    S.INSTALLMENT_PENDING: {S.SIGNED, S.CONFIRMED, S.CANCELLED},
    S.PAID: {S.PICKING, S.CANCELLED},
    S.SIGNED: {S.PICKING, S.CANCELLED},
    S.COD: {S.PICKING, S.CANCELLED},
    S.PICKING: {S.HANDED_TO_CARRIER, S.CANCELLED},
    S.HANDED_TO_CARRIER: {S.DELIVERED},
    S.DELIVERED: {S.COMPLETED, S.RETURN_REQUESTED},
    S.COMPLETED: {S.RETURN_REQUESTED},
    S.RETURN_REQUESTED: {S.INSPECTED, S.COMPLETED},
    S.INSPECTED: {S.REFUNDED, S.COMPLETED},
    S.CANCELLED: set(),
    S.REFUNDED: set(),
}

FINAL = {status for status, targets in TRANSITIONS.items() if not targets}
CANCELLABLE = {status for status, targets in TRANSITIONS.items() if S.CANCELLED in targets}
# После оплаты отменяет менеджер — с возвратом денег.
CUSTOMER_CANCELLABLE = {S.SOURCING, S.CONFIRMED, S.AWAITING_PAYMENT}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())
