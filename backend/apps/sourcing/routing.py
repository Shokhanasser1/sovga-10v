"""Выбор источника товара и наличие для витрины."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db.models import Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from apps.catalog.models import Variant

from .models import Offer

LEAD_DAY_PENALTY = Decimal("0.01")

IN_STOCK = "in_stock"
ON_ORDER = "on_order"
OUT_OF_STOCK = "out_of_stock"


@dataclass(frozen=True)
class Availability:
    status: str  # in_stock | on_order | out_of_stock
    lead_time_days: int | None


def offer_score(cost_usd: Decimal, lead_time_days: int, reliability: Decimal) -> Decimal:
    """Меньше — лучше: каждый день срока +1 % к цене, цена делится на надёжность."""
    return cost_usd * (1 + LEAD_DAY_PENALTY * lead_time_days) / reliability


def _active_reservations(now: datetime, prefix: str = "") -> Q:
    return Q(**{f"{prefix}released_at__isnull": True, f"{prefix}expires_at__gt": now})


def available_qty(offer: Offer, now: datetime) -> int:
    reserved = offer.reservations.filter(_active_reservations(now)).aggregate(
        total=Coalesce(Sum("qty"), 0)
    )["total"]
    return max(offer.qty_available - reserved, 0)


def _candidates(variant: Variant, now: datetime) -> list[Offer]:
    """Активные предложения активных источников с полем free = остаток − резервы."""
    offers: QuerySet[Offer] = (
        variant.offers.filter(is_active=True)
        .select_related("supplier", "warehouse")
        .annotate(
            reserved=Coalesce(
                Sum("reservations__qty", filter=_active_reservations(now, "reservations__")), 0
            )
        )
    )
    result = []
    for offer in offers:
        source_active = offer.warehouse.is_active if offer.is_own else offer.supplier.is_active
        if source_active:
            offer.free = max(offer.qty_available - offer.reserved, 0)
            result.append(offer)
    return result


def choose_offer(variant: Variant, qty: int, now: datetime) -> Offer | None:
    """Свой склад (дешевле — раньше), иначе свежий поставщик с лучшим баллом."""
    usable = [o for o in _candidates(variant, now) if o.free >= qty and o.is_fresh(now)]
    own = [o for o in usable if o.is_own]
    if own:
        return min(own, key=lambda o: (o.cost_usd, o.pk))
    suppliers = [o for o in usable if not o.is_own]
    if not suppliers:
        return None
    return min(
        suppliers,
        key=lambda o: (offer_score(o.cost_usd, o.lead_time_days, o.supplier.reliability), o.pk),
    )


def availability(variant: Variant, now: datetime) -> Availability:
    """Устаревший остаток поставщика — только «под заказ», никогда «в наличии»."""
    offers = [o for o in _candidates(variant, now) if o.free > 0]
    fresh = [o for o in offers if o.is_fresh(now)]
    if fresh:
        return Availability(IN_STOCK, min(o.lead_time_days for o in fresh))
    if offers:
        return Availability(ON_ORDER, min(o.lead_time_days for o in offers) + 1)
    return Availability(OUT_OF_STOCK, None)
