from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import Status
from apps.pricing.models import ExchangeRate, MarkupRule
from apps.pricing.repricing import reprice_variant
from apps.promo.models import GiftPolicy
from apps.sourcing.models import Offer

pytestmark = pytest.mark.django_db

URL = "/api/v1/pricing/products/{}/"


@pytest.fixture
def priced(variant, warehouse):
    MarkupRule.objects.create(markup_pct=Decimal("10"), min_margin_uzs=0, rounding_step_uzs=1000)
    Offer.objects.create(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"),
                         qty_available=2, last_confirmed_at=timezone.now())
    rate = ExchangeRate.objects.create(date=date(2026, 10, 8), cbu_rate=Decimal("12800"),
                                       spread_pct=Decimal("0"))
    reprice_variant(variant, rate, timezone.now())
    GiftPolicy.objects.create(name="общая", budget_pct_of_net_margin=Decimal("10"),
                              budget_cap_uzs=150_000)
    return variant


def test_price_availability_and_gift_budget(priced, client):
    response = client.get(URL.format("iphone-16-pro"))

    assert response.status_code == 200
    assert response.json() == [{
        "sku": priced.sku,
        "price_uzs": 14_080_000,
        "availability": {"status": "in_stock", "lead_time_days": 0},
        "gift_budget_uzs": 128_000,
    }]


def test_unpriced_variant(variant, client):
    [item] = client.get(URL.format("iphone-16-pro")).json()

    assert item["price_uzs"] is None
    assert item["availability"] == {"status": "out_of_stock", "lead_time_days": None}
    assert item["gift_budget_uzs"] == 0


def test_draft_variants_hidden(priced, iphone, make_variant, client):
    make_variant(iphone, "DRAFT-1", {"storage_gb": 512, "color": "white"}).save()

    skus = [item["sku"] for item in client.get(URL.format("iphone-16-pro")).json()]

    assert skus == [priced.sku]


def test_draft_or_unknown_product_is_404(priced, iphone, client):
    iphone.status = Status.DRAFT
    iphone.save()

    assert client.get(URL.format("iphone-16-pro")).status_code == 404
    assert client.get(URL.format("nope")).status_code == 404
