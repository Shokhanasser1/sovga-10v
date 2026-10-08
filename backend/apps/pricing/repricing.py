"""Актуальная цена варианта: снимки и пересчёт по закупке, правилу и курсу."""

from dataclasses import dataclass, field
from datetime import datetime

from apps.catalog.models import Status, Variant
from apps.sourcing.routing import choose_offer

from .calculator import PriceInputs, needs_reprice, sale_price_uzs
from .markup import resolve_markup_rule
from .models import ExchangeRate, MarkupRule, PriceSnapshot


@dataclass
class RepriceResult:
    changed: int = 0
    unpriced: int = 0
    missing_rule: list[str] = field(default_factory=list)


def current_price(variant: Variant) -> PriceSnapshot | None:
    return variant.price_snapshots.order_by("-computed_at", "-pk").first()


def reprice_variant(variant: Variant, rate: ExchangeRate, now: datetime) -> PriceSnapshot | None:
    """Новый снимок только если цена изменилась. Курс сдвинулся ≤ 0,5 % — считаем по прежнему.

    Без предложения цена не меняется; нет правила наценки — MarkupRule.DoesNotExist.
    """
    offer = choose_offer(variant, 1, now)
    if offer is None:
        return None
    rule = resolve_markup_rule(variant)
    latest = current_price(variant)
    effective_rate = rate.effective_rate
    if latest is not None and not needs_reprice(latest.rate, effective_rate):
        effective_rate = latest.rate
    price = sale_price_uzs(
        PriceInputs(
            cost_usd=offer.cost_usd,
            rate=effective_rate,
            markup_pct=rule.markup_pct,
            min_margin_uzs=rule.min_margin_uzs,
            rounding_step_uzs=rule.rounding_step_uzs,
        )
    )
    if (
        latest is not None
        and latest.price_uzs == price
        and latest.cost_usd == offer.cost_usd
        and latest.offer_id == offer.pk
    ):
        return latest
    return PriceSnapshot.objects.create(
        variant=variant, price_uzs=price, cost_usd=offer.cost_usd, rate=effective_rate,
        offer=offer, markup_rule=rule,
    )


def reprice_all(rate: ExchangeRate, now: datetime) -> RepriceResult:
    result = RepriceResult()
    variants = Variant.objects.exclude(status=Status.ARCHIVED).select_related(
        "product_model__category"
    )
    for variant in variants.order_by("sku"):
        before = current_price(variant)
        try:
            snapshot = reprice_variant(variant, rate, now)
        except MarkupRule.DoesNotExist:
            result.missing_rule.append(variant.sku)
            continue
        if snapshot is None:
            result.unpriced += 1
        elif before is None or snapshot.pk != before.pk:
            result.changed += 1
    return result
