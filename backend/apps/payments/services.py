"""Как оплата меняет заказ. Все переходы — через машину состояний, проверка статуса под блокировкой."""

from datetime import datetime, timedelta

from django.db import transaction

from apps.notifications.outbox import emit
from apps.orders.models import Order
from apps.orders.services import PICKING_HOLD, PRICE_LOCK, transition
from apps.sourcing.models import Reservation

S = Order.Status
PAYMENT_WINDOW = timedelta(hours=12)  # тайм-аут транзакции Payme
PAYABLE = {S.CONFIRMED, S.AWAITING_PAYMENT}
REFUNDABLE = {S.PAID, S.PICKING}


def _hold(order: Order, until: datetime) -> None:
    Reservation.objects.filter(ref=order.number, released_at__isnull=True).update(expires_at=until)


@transaction.atomic
def start_payment(order: Order, now: datetime, actor: str) -> Order:
    """Провайдер начал транзакцию: заказ ждёт оплату 12 часов, товар на это время держим."""
    current = Order.objects.select_for_update().get(pk=order.pk)
    if current.status != S.AWAITING_PAYMENT:
        current = transition(
            current, S.AWAITING_PAYMENT, now, actor, "Начата оплата",
            allowed_from={S.CONFIRMED}, denied_message="Этот заказ сейчас нельзя оплатить",
        )
    current.price_lock_until = now + PAYMENT_WINDOW
    current.save(update_fields=["price_lock_until"])
    _hold(current, current.price_lock_until)
    order.status = current.status
    return current


@transaction.atomic
def confirm_payment(order: Order, now: datetime, actor: str, provider: str) -> Order:
    paid = transition(
        order, S.PAID, now, actor, f"Оплачен через {provider}",
        allowed_from={S.AWAITING_PAYMENT}, denied_message="Оплата для этого заказа не начиналась",
    )
    _hold(paid, now + PICKING_HOLD)
    emit("order.paid", {"number": paid.number, "total": paid.total_uzs, "provider": provider}, now)
    return paid


@transaction.atomic
def fail_payment(order: Order, now: datetime, actor: str) -> Order:
    """Транзакция отменена до проведения — покупатель может попробовать снова, ещё 30 минут."""
    current = Order.objects.select_for_update().get(pk=order.pk)
    if current.status != S.AWAITING_PAYMENT:
        return current
    current = transition(current, S.CONFIRMED, now, actor, "Оплата не прошла")
    current.price_lock_until = now + PRICE_LOCK
    current.save(update_fields=["price_lock_until"])
    _hold(current, current.price_lock_until)
    order.status = current.status
    return current


def refund_payment(order: Order, now: datetime, actor: str) -> Order:
    """Провайдер отменил проведённый платёж: деньги вернутся, заказ отменяется (до передачи курьеру)."""
    return transition(
        order, S.CANCELLED, now, actor, "Платёж отменён провайдером — деньги возвращаются",
        allowed_from=REFUNDABLE, denied_message="Заказ уже передан курьеру — возврат только через возврат товара",
    )
