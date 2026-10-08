from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.pricing.models import ExchangeRate, MarkupRule, PriceSnapshot
from apps.pricing.repricing import RepriceResult, current_price, reprice_all, reprice_variant
from apps.sourcing.models import Offer

pytestmark = pytest.mark.django_db

NOW = timezone.now()


def rate(value, day=8):
    return ExchangeRate.objects.create(
        date=date(2026, 10, day), cbu_rate=Decimal(value), spread_pct=Decimal("0")
    )


@pytest.fixture
def priced(variant, warehouse):
    MarkupRule.objects.create(markup_pct=Decimal("10"), min_margin_uzs=0, rounding_step_uzs=1000)
    Offer.objects.create(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"),
                         qty_available=2, last_confirmed_at=NOW)
    return variant


def test_first_price(priced):
    snapshot = reprice_variant(priced, rate("12800"), NOW)

    assert (snapshot.price_uzs, snapshot.cost_usd, snapshot.rate) == (14_080_000, Decimal("1000"), Decimal("12800"))
    assert current_price(priced) == snapshot


def test_nothing_changed_no_new_snapshot(priced):
    first = reprice_variant(priced, rate("12800"), NOW)

    assert reprice_variant(priced, rate("12800", day=9), NOW) == first
    assert PriceSnapshot.objects.count() == 1


def test_small_rate_move_keeps_price(priced):
    first = reprice_variant(priced, rate("12800"), NOW)

    assert reprice_variant(priced, rate("12860", day=9), NOW) == first  # +0.47 %


def test_big_rate_move_reprices(priced):
    reprice_variant(priced, rate("12800"), NOW)

    snapshot = reprice_variant(priced, rate("12870", day=9), NOW)  # +0.55 %

    assert snapshot.price_uzs == 14_157_000
    assert current_price(priced) == snapshot


def test_cost_change_reprices_at_held_rate(priced):
    reprice_variant(priced, rate("12800"), NOW)
    Offer.objects.update(cost_usd=Decimal("1100"))

    snapshot = reprice_variant(priced, rate("12830", day=9), NOW)

    assert (snapshot.price_uzs, snapshot.rate) == (15_488_000, Decimal("12800"))


def test_rule_change_reprices(priced):
    reprice_variant(priced, rate("12800"), NOW)
    MarkupRule.objects.update(markup_pct=Decimal("12"))

    assert reprice_variant(priced, rate("12800", day=9), NOW).price_uzs == 14_336_000


def test_no_offer_no_price(variant):
    MarkupRule.objects.create(markup_pct=Decimal("10"))

    assert reprice_variant(variant, rate("12800"), NOW) is None
    assert current_price(variant) is None


def test_reprice_all_reports(priced, iphone, make_variant):
    make_variant(iphone, "IP16P-512-W", {"storage_gb": 512, "color": "white"}).save()

    result = reprice_all(rate("12800"), NOW)

    assert result == RepriceResult(changed=1, unpriced=1, missing_rule=[])


def test_reprice_all_lists_variants_without_rule(priced):
    MarkupRule.objects.all().delete()

    assert reprice_all(rate("12800"), NOW).missing_rule == [priced.sku]
