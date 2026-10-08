"""Гарантия по IMEI: когда и кому продано, до какого числа гарантия, у кого куплено."""

import calendar
from dataclasses import dataclass, field
from datetime import datetime

from django.db.models import Q

from apps.catalog.labels import variant_title
from apps.delivery.models import Shipment
from apps.inventory.models import InventoryUnit
from apps.orders.services import OrderError

from .models import WarrantyCase


def add_months(moment: datetime, months: int) -> datetime:
    """31 января + 1 месяц = 28 (29) февраля."""
    index = moment.month - 1 + months
    year, month = moment.year + index // 12, index % 12 + 1
    return moment.replace(year=year, month=month, day=min(moment.day, calendar.monthrange(year, month)[1]))


def find_sold_unit(value: str) -> InventoryUnit | None:
    value = value.strip()
    if not value:
        return None
    return (
        InventoryUnit.objects.filter(Q(imei1=value) | Q(imei2=value) | Q(serial=value), status=InventoryUnit.State.SOLD)
        .select_related("variant__product_model__category", "order_line__order__customer", "order_line__offer__supplier",
                        "purchase_batch__supplier", "warehouse")
        .first()
    )


@dataclass
class WarrantyInfo:
    unit: InventoryUnit
    title: str
    order: object
    customer_phone: str
    sold_at: datetime | None
    until: datetime | None
    source: str
    cases: list = field(default_factory=list)

    def is_active(self, now: datetime) -> bool:
        return self.until is not None and now <= self.until


def _source(unit: InventoryUnit) -> str:
    """У кого куплено: поставщик под заказ, поставщик партии или свой склад."""
    line = unit.order_line
    if line and line.offer and line.offer.supplier:
        return line.offer.supplier.name
    if unit.purchase_batch and unit.purchase_batch.supplier:
        return unit.purchase_batch.supplier.name
    return unit.warehouse.name


def warranty_info(unit: InventoryUnit) -> WarrantyInfo:
    order = unit.order_line.order if unit.order_line else None
    sold_at = Shipment.objects.filter(order=order).values_list("handed_at", flat=True).first() if order else None
    months = unit.variant.product_model.category.warranty_months
    return WarrantyInfo(
        unit=unit, title=variant_title(unit.variant), order=order,
        customer_phone=order.customer.phone if order else "", sold_at=sold_at,
        until=add_months(sold_at, months) if sold_at else None, source=_source(unit),
        cases=list(unit.warranty_cases.all()),
    )


def open_case(unit: InventoryUnit, complaint: str, service_center: str, now: datetime, actor: str) -> WarrantyCase:
    complaint = complaint.strip()
    if not complaint:
        raise OrderError("Опишите неисправность со слов покупателя")
    info = warranty_info(unit)
    if info.until is None:
        raise OrderError("Устройство не продавалось через магазин — гарантии нет")
    if not info.is_active(now):
        raise OrderError(f"Гарантия закончилась {info.until:%d.%m.%Y}")
    return WarrantyCase.objects.create(
        unit=unit, complaint=complaint[:500], service_center=service_center.strip()[:200], opened_at=now, opened_by=actor
    )
