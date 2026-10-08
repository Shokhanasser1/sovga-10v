from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import ProductModel, Status
from apps.pricing.listing import refresh_listing_cache
from apps.pricing.models import PriceSnapshot
from apps.sourcing.models import Offer

pytestmark = pytest.mark.django_db

NOW = timezone.now()


def price(variant, amount):
    PriceSnapshot.objects.create(variant=variant, price_uzs=amount, cost_usd=Decimal("900"), rate=Decimal("12800"))


@pytest.fixture
def two_variants(variant, iphone, make_variant, warehouse):
    cheap = make_variant(iphone, "IP16P-128-W", {"storage_gb": 128, "color": "white"}, status=Status.ACTIVE)
    cheap.save()
    price(variant, 14_080_000)
    price(cheap, 12_000_000)
    return variant, cheap


def refreshed(product):
    refresh_listing_cache(NOW)
    return ProductModel.objects.get(pk=product.pk)


def test_price_from_counts_only_available_variants(two_variants, iphone, warehouse):
    in_stock, _sold_out = two_variants
    Offer.objects.create(variant=in_stock, warehouse=warehouse, cost_usd=Decimal("1000"),
                         qty_available=2, last_confirmed_at=NOW)

    product = refreshed(iphone)

    assert (product.price_from_uzs, product.is_available) == (14_080_000, True)


def test_unavailable_product_shows_lowest_known_price(two_variants, iphone):
    product = refreshed(iphone)

    assert (product.price_from_uzs, product.is_available) == (12_000_000, False)


def test_product_without_prices(iphone):
    product = refreshed(iphone)

    assert (product.price_from_uzs, product.is_available) == (None, False)


def test_draft_variants_are_ignored(two_variants, iphone):
    _, cheap = two_variants
    cheap.status = Status.DRAFT
    cheap.save()

    assert refreshed(iphone).price_from_uzs == 14_080_000
