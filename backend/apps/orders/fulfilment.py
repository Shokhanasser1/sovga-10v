"""Сборка заказа: устройство с IMEI на каждую единицу поштучного товара, отметка UzIMEI.

Без всех IMEI и отметок UzIMEI заказ не отгружается (спецификация, раздел 3.2 п. 4).
"""

from dataclasses import asdict
from datetime import datetime

from django.db import transaction
from django.db.models import Count, F, Q, QuerySet, Value
from django.db.models.functions import Greatest

from apps.catalog.labels import variant_title
from apps.delivery.carriers import CARRIERS, Handover, HandoverError
from apps.delivery.models import Shipment

from apps.inventory.imei import is_valid_imei
from apps.notifications.outbox import emit
from apps.inventory.models import InventoryUnit
from apps.inventory.services import release_unit, sync_own_offer
from apps.sourcing.models import Offer, Reservation, Supplier, Warehouse
from apps.sourcing.reservations import release

from .models import Order, OrderLine
from .services import OrderError, money, transition

S = Order.Status
U = InventoryUnit.State
Z = InventoryUnit.UzimeiStatus
PICKABLE = {S.PAID, S.SIGNED, S.COD}


@transaction.atomic
def start_picking(order: Order, now: datetime, actor: str) -> Order:
    picking = transition(
        order, S.PICKING, now, actor, note="Сборка начата",
        allowed_from=PICKABLE, denied_message="Собирать можно только оплаченный заказ",
    )
    emit("fulfilment.started", {"number": picking.number}, now)  # поставщикам — прислать IMEI
    return picking


def _lock_picking(order_id: int) -> Order:
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != S.PICKING:
        raise OrderError("Заказ сейчас не собирается")
    return order


def _is_serialized(line: OrderLine) -> bool:
    return line.variant.product_model.category.is_serialized


def _receiving_warehouse() -> Warehouse:
    warehouse = Warehouse.objects.order_by("pk").first()
    if warehouse is None:
        raise OrderError("Нет ни одного склада — создайте склад в админке")
    return warehouse


@transaction.atomic
def add_unit(line: OrderLine, imei: str, now: datetime, actor: str, uzimei_registered: bool = False) -> InventoryUnit:
    """Скан IMEI. Свой склад — находим устройство на складе; поставщик — принимаем новое устройство."""
    _lock_picking(line.order_id)
    line = OrderLine.objects.select_related("variant__product_model__category", "offer").get(pk=line.pk)
    if not _is_serialized(line):
        raise OrderError("Этот товар без IMEI — устройство не нужно")
    imei = imei.strip()
    if not is_valid_imei(imei):
        raise OrderError("Неверный IMEI: нужно 15 цифр с верной контрольной цифрой")
    if line.units.count() >= line.qty:
        raise OrderError("Для этой строки уже есть все устройства")
    unit = InventoryUnit.objects.select_for_update().filter(Q(imei1=imei) | Q(imei2=imei)).first()
    registered = {"uzimei_status": Z.REGISTERED} if uzimei_registered else {}
    if line.offer and line.offer.is_own:
        if unit is None:
            raise OrderError(f"На складе нет устройства с IMEI {imei} — проверьте скан")
        if unit.variant_id != line.variant_id:
            raise OrderError(f"Это устройство другой модификации: {variant_title(unit.variant)}")
        if unit.status != U.IN_STOCK or unit.order_line_id:
            raise OrderError("Это устройство уже продано или собрано в другой заказ")
        unit.status, unit.order_line = U.RESERVED, line
        for field, value in registered.items():
            setattr(unit, field, value)
        unit.save()
        return unit
    if unit is not None:
        raise OrderError("Устройство с таким IMEI уже есть в системе")
    unit = InventoryUnit(
        variant=line.variant, warehouse=_receiving_warehouse(), imei1=imei, cost_usd=line.cost_usd,
        status=U.RESERVED, order_line=line, received_for_order=True, **registered,
    )
    unit.full_clean()
    unit.save()
    return unit


@transaction.atomic
def remove_unit(unit: InventoryUnit, now: datetime, actor: str) -> None:
    unit = InventoryUnit.objects.select_related("order_line").get(pk=unit.pk)
    if unit.order_line is None:
        raise OrderError("Устройство не привязано к заказу")
    _lock_picking(unit.order_line.order_id)
    release_unit(unit)


@transaction.atomic
def mark_uzimei(unit: InventoryUnit, registered: bool, now: datetime, actor: str) -> InventoryUnit:
    unit = InventoryUnit.objects.select_related("order_line").get(pk=unit.pk)
    if unit.order_line is None:
        raise OrderError("Устройство не привязано к заказу")
    _lock_picking(unit.order_line.order_id)
    unit.uzimei_status = Z.REGISTERED if registered else Z.NOT_REGISTERED
    unit.save(update_fields=["uzimei_status"])
    return unit


def picking_problems(order: Order) -> list[str]:
    """Что мешает отгрузке. Пустой список — можно передавать курьеру."""
    problems = []
    for line in order.lines.select_related("variant__product_model__category").order_by("pk"):
        if not _is_serialized(line):
            continue
        units = list(line.units.order_by("pk"))
        if len(units) < line.qty:
            problems.append(f"{variant_title(line.variant)}: нужно ещё {line.qty - len(units)} IMEI")
        for unit in units:
            if unit.uzimei_status == Z.NOT_REGISTERED:
                problems.append(f"IMEI {unit.imei1}: не зарегистрирован в UzIMEI — замените устройство")
            elif unit.uzimei_status != Z.REGISTERED:
                problems.append(f"IMEI {unit.imei1}: нет отметки UzIMEI")
    return problems


def _write_off(order: Order, now: datetime) -> None:
    """Товар ушёл: устройства проданы, резервы сняты, остатки предложений уменьшены."""
    InventoryUnit.objects.filter(order_line__order=order).update(status=U.SOLD)
    for reservation in Reservation.objects.filter(ref=order.number, released_at__isnull=True):
        release(reservation, now)
    for line in order.lines.select_related("offer__warehouse", "variant__product_model__category"):
        if line.offer is None:
            continue
        if line.offer.is_own and _is_serialized(line):
            sync_own_offer(line.variant, line.offer.warehouse)  # свой остаток = устройства на складе
        else:
            Offer.objects.filter(pk=line.offer_id).update(
                qty_available=Greatest(F("qty_available") - line.qty, Value(0))
            )


@transaction.atomic
def ship(order: Order, carrier_code: str, handover: Handover, now: datetime, actor: str) -> Order:
    """Передача курьеру или в службу доставки — только собранный заказ со всеми IMEI и отметками UzIMEI."""
    locked = _lock_picking(order.pk)
    problems = picking_problems(locked)
    if problems:
        raise OrderError("Нельзя отгрузить: " + "; ".join(problems))
    carrier = CARRIERS.get(carrier_code)
    if carrier is None:
        raise OrderError("Неизвестный способ доставки")
    try:
        handover = carrier.prepare(handover)
    except HandoverError as error:
        raise OrderError(error.message) from error
    Shipment.objects.create(order=locked, carrier=carrier.code, handed_at=now, **asdict(handover))
    _write_off(locked, now)
    return transition(
        locked, S.HANDED_TO_CARRIER, now, actor, note=carrier.describe(handover), allowed_from={S.PICKING}
    )


@transaction.atomic
def deliver(order: Order, now: datetime, actor: str) -> Order:
    note = "Доставлен"
    if order.payment_method == Order.PaymentMethod.COD:
        note += f", оплата при получении: {money(order.total_uzs)} сум"
    delivered = transition(
        order, S.DELIVERED, now, actor, note=note,
        allowed_from={S.HANDED_TO_CARRIER}, denied_message="Заказ ещё не передан в доставку",
    )
    Shipment.objects.filter(order=delivered).update(delivered_at=now)
    return delivered


def waiting_for_supplier_imei(chat_id: int, number: str = "") -> QuerySet[OrderLine]:
    """Строки собираемых заказов, где поставщик из этого чата ещё не прислал все IMEI. Старые — первыми."""
    lines = (
        OrderLine.objects.filter(
            order__status=S.PICKING, offer__supplier__telegram_chat_id=chat_id,
            variant__product_model__category__is_serialized=True,
        )
        .annotate(bound=Count("units"))
        .filter(bound__lt=F("qty"))
        .select_related("order", "offer", "variant__product_model__category")
        .order_by("order__created_at", "pk")
    )
    return lines.filter(order__number=number) if number else lines


def add_supplier_unit(chat_id: int, imei: str, number: str, now: datetime) -> str | None:
    """IMEI, присланный поставщиком в бот. None — чат не поставщика: сообщение не нам."""
    if not Supplier.objects.filter(telegram_chat_id=chat_id).exists():
        return None
    line = waiting_for_supplier_imei(chat_id, number).first()
    if line is None:
        return f"По заказу {number} IMEI сейчас не нужен" if number else "Сейчас ни по одному заказу IMEI не нужен — спасибо!"
    try:
        add_unit(line, imei, now, actor=f"supplier:{line.offer.supplier_id}")
    except OrderError as error:
        return error.message
    left = sum(item.qty - item.bound for item in waiting_for_supplier_imei(chat_id, line.order.number))
    done = f"ещё нужно {left} IMEI по этому заказу" if left else "по этому заказу всё, спасибо!"
    return f"Записали IMEI {imei}: заказ {line.order.number}, {variant_title(line.variant)} — {done}"
