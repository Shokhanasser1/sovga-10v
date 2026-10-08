"""Возвраты: оформление, приёмка со сверкой IMEI, возврат денег; автозавершение после срока возврата."""

from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from apps.delivery.models import Shipment
from apps.inventory.models import InventoryUnit

from .models import Order, ReturnRequest
from .services import OrderError, transition

S = Order.Status
R = ReturnRequest.Status
U = InventoryUnit.State


def money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def return_deadline(order: Order) -> datetime | None:
    delivered_at = Shipment.objects.filter(order=order).values_list("delivered_at", flat=True).first()
    return delivered_at + timedelta(days=settings.RETURN_DAYS) if delivered_at else None


def _lock(order: Order, status: str, message: str) -> Order:
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status != status:
        raise OrderError(message)
    return locked


def _request(order: Order, status: str) -> ReturnRequest:
    request = ReturnRequest.objects.select_for_update().filter(order=order, status=status).first()
    if request is None:
        raise OrderError("Нет возврата в нужном состоянии")
    return request


@transaction.atomic
def open_return(order: Order, reason: str, now: datetime, actor: str) -> ReturnRequest:
    reason = reason.strip()
    if not reason:
        raise OrderError("Укажите причину возврата")
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status not in (S.DELIVERED, S.COMPLETED):
        raise OrderError("Вернуть можно только доставленный заказ")
    deadline = return_deadline(locked)
    if deadline is None or now > deadline:
        raise OrderError(
            f"Срок возврата ({settings.RETURN_DAYS} дн. с доставки) истёк — если товар неисправен, "
            "откройте гарантийный случай"
        )
    transition(locked, S.RETURN_REQUESTED, now, actor, note=f"Причина: {reason}", allowed_from={S.DELIVERED, S.COMPLETED})
    return ReturnRequest.objects.create(order=locked, reason=reason[:300], created_at=now)


def _devices_match(order: Order, imeis: set[str]) -> bool:
    """Принесли ровно проданные устройства: каждый IMEI — одного из них, и ни одного не забыли."""
    sold = list(InventoryUnit.objects.filter(order_line__order=order, status=U.SOLD))
    found = [next((unit.pk for unit in sold if value in (unit.imei1, unit.imei2)), None) for value in imeis]
    return None not in found and sorted(found) == sorted(unit.pk for unit in sold)


@transaction.atomic
def inspect_return(order: Order, imeis: list[str], gift_returned: bool, now: datetime, actor: str) -> ReturnRequest:
    locked = _lock(order, S.RETURN_REQUESTED, "Заказ не ждёт приёмки возврата")
    request = _request(locked, R.REQUESTED)
    received = {value.strip() for value in imeis if value.strip()}
    request.imeis_received, request.gift_returned, request.inspected_at = sorted(received), gift_returned, now
    if not _devices_match(locked, received):
        request.status, request.note = R.REJECTED, "IMEI не совпадает с проданными"
        request.save()
        transition(locked, S.COMPLETED, now, actor, note="Возврат отклонён: IMEI не совпадает с проданными",
                   allowed_from={S.RETURN_REQUESTED})
        return request
    withheld = 0 if gift_returned else sum(line.gift_value_uzs * line.qty for line in locked.lines.filter(is_gift=True))
    request.status, request.refund_amount_uzs = R.ACCEPTED, max(locked.total_uzs - withheld, 0)
    request.save()
    InventoryUnit.objects.filter(order_line__order=locked, status=U.SOLD).update(status=U.RETURNED)
    note = f"К возврату {money(request.refund_amount_uzs)} сум"
    if withheld:
        note += f" (удержана цена подарка {money(withheld)} сум)"
    transition(locked, S.INSPECTED, now, actor, note=note, allowed_from={S.RETURN_REQUESTED})
    return request


@transaction.atomic
def reject_return(order: Order, note: str, now: datetime, actor: str) -> ReturnRequest:
    note = note.strip()
    if not note:
        raise OrderError("Укажите причину отказа")
    locked = _lock(order, S.RETURN_REQUESTED, "Заказ не ждёт приёмки возврата")
    request = _request(locked, R.REQUESTED)
    request.status, request.note, request.inspected_at = R.REJECTED, note[:300], now
    request.save()
    transition(locked, S.COMPLETED, now, actor, note=f"Возврат отклонён: {note}", allowed_from={S.RETURN_REQUESTED})
    return request


@transaction.atomic
def refund_return(order: Order, now: datetime, actor: str) -> ReturnRequest:
    """Деньги уже вернули в кабинете Payme / Click — фиксируем."""
    locked = _lock(order, S.INSPECTED, "Возврат ещё не принят или деньги уже возвращены")
    request = _request(locked, R.ACCEPTED)
    request.status, request.refunded_at = R.REFUNDED, now
    request.save()
    transition(locked, S.REFUNDED, now, actor, note=f"Деньги возвращены: {money(request.refund_amount_uzs)} сум",
               allowed_from={S.INSPECTED})
    return request


@transaction.atomic
def _complete_if_still_due(pk: int, now: datetime) -> bool:
    locked = Order.objects.select_for_update().get(pk=pk)
    deadline = return_deadline(locked)
    if locked.status != S.DELIVERED or deadline is None or deadline >= now:
        return False
    transition(locked, S.COMPLETED, now, actor="system", note="Срок возврата истёк", allowed_from={S.DELIVERED})
    return True


def complete_delivered(now: datetime) -> int:
    """Доставленные заказы после срока возврата — «Завершён»."""
    border = now - timedelta(days=settings.RETURN_DAYS)
    candidates = Order.objects.filter(status=S.DELIVERED, shipment__delivered_at__lt=border).values_list("pk", flat=True)
    return sum(_complete_if_still_due(pk, now) for pk in list(candidates))
