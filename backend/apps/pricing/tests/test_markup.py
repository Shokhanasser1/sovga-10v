from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.catalog.models import Category
from apps.pricing.markup import price_for, resolve_markup_rule
from apps.pricing.models import ExchangeRate, MarkupRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def variant(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", {"storage_gb": 256, "color": "black"})
    variant.save()
    return variant


def rule(**kwargs):
    kwargs.setdefault("markup_pct", Decimal("10"))
    return MarkupRule.objects.create(**kwargs)


def test_effective_rate_adds_spread():
    rate = ExchangeRate(date=date(2026, 10, 8), cbu_rate=Decimal("12800"), spread_pct=Decimal("1"))

    assert rate.effective_rate == Decimal("12928.00")


def test_variant_rule_beats_category_rule(variant, phones):
    rule(category=phones, markup_pct=Decimal("8"))
    specific = rule(variant=variant, markup_pct=Decimal("5"))

    assert resolve_markup_rule(variant) == specific


def test_nearest_category_beats_parent(variant, phones):
    electronics = Category.objects.create(slug="electronics", name_ru="Электроника", name_uz="Elektronika")
    phones.parent = electronics
    phones.save()
    rule(category=electronics, markup_pct=Decimal("15"))
    nearest = rule(category=phones, markup_pct=Decimal("8"))

    assert resolve_markup_rule(variant) == nearest


def test_brand_rule_then_global_fallback(variant, apple):
    global_rule = rule()
    assert resolve_markup_rule(variant) == global_rule

    brand_rule = rule(brand=apple, markup_pct=Decimal("7"))
    assert resolve_markup_rule(variant) == brand_rule


def test_inactive_rules_are_ignored(variant, phones):
    rule(category=phones, is_active=False)

    with pytest.raises(MarkupRule.DoesNotExist):
        resolve_markup_rule(variant)


def test_rule_with_two_scopes_is_invalid(variant, phones):
    invalid = MarkupRule(variant=variant, category=phones, markup_pct=Decimal("5"))

    with pytest.raises(ValidationError):
        invalid.full_clean()


def test_only_one_active_global_rule():
    rule()

    with pytest.raises(IntegrityError):
        rule()


def test_price_for_uses_rule_and_effective_rate(variant, phones):
    rule(category=phones, markup_pct=Decimal("10"), min_margin_uzs=0, rounding_step_uzs=1000)
    rate = ExchangeRate.objects.create(
        date=date(2026, 10, 8), cbu_rate=Decimal("12800"), spread_pct=Decimal("1")
    )

    # 1000 × 12 928 × 1.1 = 14 220 800 → 14 221 000
    assert price_for(variant, Decimal("1000"), rate) == 14_221_000
