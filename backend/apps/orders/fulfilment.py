"""Сборка заказа: устройство с IMEI на каждую единицу поштучного товара, отметка UzIMEI.

Без всех IMEI и отметок UzIMEI заказ не отгружается (спецификация, раздел 3.2 п. 4).
"""

from datetime import datetime

from django.db import transaction
from django.db.models import Q

from apps.inventory.imei import is_valid_imei
from apps.inventory.models import InventoryUnit
from apps.sourcing.matching import variant_label
from apps.sourcing.models import Warehouse

from .models import Order, OrderLine
from .services import OrderError, transition

S = Order.Status
U = InventoryUnit.State
Z = InventoryUnit.UzimeiStatus
PICKABLE = {S.PAID, S.SIGNED, S.COD}


def start_picking(order: Order, now: datetime, actor: str) -> Order:
    return transition(
        order, S.PICKING, now, actor, note="Сборка начата",
        allowed_from=PICKABLE, denied_message="Собирать можно только оплаченный заказ",
    )


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
            raise OrderError(f"Это устройство другой модификации: {variant_label(unit.variant)}")
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
        status=U.RESERVED, order_line=line, **registered,
    )
    unit.full_clean()
    unit.save()
    return unit


def _release(unit: InventoryUnit) -> None:
    """Своё устройство — обратно на склад; устройство поставщика, принятое под заказ, — забываем."""
    if unit.order_line.offer and unit.order_line.offer.is_own:
        unit.status, unit.order_line = U.IN_STOCK, None
        unit.save(update_fields=["status", "order_line"])
    else:
        unit.delete()


@transaction.atomic
def remove_unit(unit: InventoryUnit, now: datetime, actor: str) -> None:
    unit = InventoryUnit.objects.select_related("order_line__offer").get(pk=unit.pk)
    if unit.order_line is None:
        raise OrderError("Устройство не привязано к заказу")
    _lock_picking(unit.order_line.order_id)
    _release(unit)


def release_units(order: Order) -> None:
    """Заказ отменён во время сборки."""
    for unit in InventoryUnit.objects.select_related("order_line__offer").filter(order_line__order=order):
        _release(unit)


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
            problems.append(f"{variant_label(line.variant)}: нужно ещё {line.qty - len(units)} IMEI")
        for unit in units:
            if unit.uzimei_status == Z.NOT_REGISTERED:
                problems.append(f"IMEI {unit.imei1}: не зарегистрирован в UzIMEI — замените устройство")
            elif unit.uzimei_status != Z.REGISTERED:
                problems.append(f"IMEI {unit.imei1}: нет отметки UzIMEI")
    return problems
