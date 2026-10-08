"""Магазин для тестов заказа: iPhone на своём складе, чехлы-подарки, политика подарка."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import AccessoryCompat, Brand, Category, ProductModel, Status
from apps.pricing.models import ExchangeRate, PriceSnapshot
from apps.promo.models import GiftPolicy
from apps.sourcing.models import Offer

NOW = timezone.now()


def price(variant, amount, cost_usd="1000", rate="12800"):
    return PriceSnapshot.objects.create(
        variant=variant, price_uzs=amount, cost_usd=Decimal(cost_usd), rate=Decimal(rate)
    )


def stock(variant, qty, warehouse=None, supplier=None, confirmed_at=None):
    return Offer.objects.create(
        variant=variant, warehouse=warehouse, supplier=supplier, cost_usd=Decimal("1000"),
        qty_available=qty, last_confirmed_at=confirmed_at or NOW,
    )


@pytest.fixture
def shop(variant, phones, iphone, warehouse, make_variant, make_supplier):
    ExchangeRate.objects.create(date=date(2026, 10, 8), cbu_rate=Decimal("12800"), spread_pct=Decimal("0"))
    price(variant, 14_080_000)
    stock(variant, 3, warehouse=warehouse)

    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    spigen = Brand.objects.create(slug="spigen", name="Spigen")

    def accessory(slug, sku, amount, giftable=True, compatible=True, **source):
        product = ProductModel.objects.create(
            category=cases, brand=spigen, slug=slug, name_ru=f"Чехол {slug}", name_uz=f"G'ilof {slug}",
            is_accessory=True, status=Status.ACTIVE,
        )
        if compatible:
            AccessoryCompat.objects.create(accessory=product, device=iphone)
        item = make_variant(product, sku, {}, giftable=giftable, status=Status.ACTIVE)
        item.save()
        price(item, amount, cost_usd="5")
        stock(item, 10, **source)
        return item

    supplier = make_supplier("Чехлы оптом")
    gifts = {
        "case": accessory("case", "CASE-1", 120_000, warehouse=warehouse),
        "expensive": accessory("premium", "CASE-PREMIUM", 200_000, warehouse=warehouse),
        "supplier_only": accessory("remote", "CASE-REMOTE", 90_000, supplier=supplier),
        "not_giftable": accessory("plain", "CASE-PLAIN", 50_000, giftable=False, warehouse=warehouse),
        "incompatible": accessory("other", "CASE-OTHER", 60_000, compatible=False, warehouse=warehouse),
    }
    GiftPolicy.objects.create(name="Смартфоны", category=phones, budget_pct_of_net_margin=Decimal("10"),
                              budget_cap_uzs=150_000)
    return {"phone": variant, "warehouse": warehouse, "supplier": supplier, **gifts}
