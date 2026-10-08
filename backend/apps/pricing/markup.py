"""Публичный сервис цен: выбор правила наценки и цена варианта."""

from decimal import Decimal

from apps.catalog.models import Variant

from .calculator import PriceInputs, sale_price_uzs
from .models import ExchangeRate, MarkupRule


def resolve_markup_rule(variant: Variant) -> MarkupRule:
    """Вариант → ближайшая категория → бренд → глобальное правило."""
    active = MarkupRule.objects.filter(is_active=True)
    rule = active.filter(variant=variant).first()
    if rule:
        return rule
    for category in reversed(variant.product_model.category.lineage()):
        rule = active.filter(category=category).first()
        if rule:
            return rule
    rule = active.filter(brand_id=variant.product_model.brand_id).first()
    if rule:
        return rule
    rule = active.filter(variant__isnull=True, category__isnull=True, brand__isnull=True).first()
    if rule:
        return rule
    raise MarkupRule.DoesNotExist("Нет активного правила наценки, даже общего")


def price_for(variant: Variant, cost_usd: Decimal, rate: ExchangeRate) -> int:
    rule = resolve_markup_rule(variant)
    return sale_price_uzs(
        PriceInputs(
            cost_usd=cost_usd,
            rate=rate.effective_rate,
            markup_pct=rule.markup_pct,
            min_margin_uzs=rule.min_margin_uzs,
            rounding_step_uzs=rule.rounding_step_uzs,
        )
    )
