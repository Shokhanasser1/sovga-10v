"""Приёмка устройств и синхронизация своего предложения."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.catalog.models import Variant
from apps.sourcing.models import Offer, Warehouse

from .models import InventoryUnit, PurchaseBatch


@transaction.atomic
def receive_unit(
    *,
    variant: Variant,
    warehouse: Warehouse,
    cost_usd: Decimal,
    imei1: str = "",
    imei2: str = "",
    serial: str = "",
    batch: PurchaseBatch | None = None,
) -> InventoryUnit:
    unit = InventoryUnit(
        variant=variant, warehouse=warehouse, cost_usd=cost_usd, imei1=imei1, imei2=imei2,
        serial=serial, purchase_batch=batch,
    )
    unit.full_clean()
    unit.save()
    sync_own_offer(variant, warehouse)
    return unit


def sync_own_offer(variant: Variant, warehouse: Warehouse) -> Offer | None:
    """Своё предложение = единицы на складе: количество и средняя себестоимость."""
    stats = InventoryUnit.objects.filter(
        variant=variant, warehouse=warehouse, status=InventoryUnit.State.IN_STOCK
    ).aggregate(count=Count("pk"), avg_cost=Avg("cost_usd"))
    offer = Offer.objects.filter(variant=variant, warehouse=warehouse).first()
    if offer is None and stats["count"] == 0:
        return None
    if offer is None:
        offer = Offer(variant=variant, warehouse=warehouse, lead_time_days=0)
    offer.qty_available = stats["count"]
    if stats["avg_cost"] is not None:
        offer.cost_usd = Decimal(str(stats["avg_cost"])).quantize(Decimal("0.01"))
    offer.last_confirmed_at = timezone.now()
    offer.is_active = True
    offer.save()
    return offer
