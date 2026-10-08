import pytest
from django.core.management import call_command

from apps.catalog.models import ProductModel, Variant
from apps.catalog.search import search_products
from apps.inventory.models import InventoryUnit

pytestmark = pytest.mark.django_db


def seed():
    call_command("seed_demo", stdout=None)


def test_seed_demo_builds_a_sellable_catalog(client):
    seed()

    iphone = ProductModel.objects.get(slug="iphone-16-pro")
    assert iphone.price_from_uzs and iphone.is_available
    assert InventoryUnit.objects.filter(variant__product_model=iphone).exists()
    assert search_products("айфон 16")[0] == iphone

    offers = client.get("/api/v1/pricing/products/iphone-16-pro/").json()
    assert any(item["gift_budget_uzs"] > 0 for item in offers)
    statuses = {item["availability"]["status"] for slug in ("iphone-16-pro", "galaxy-s25-ultra", "redmi-note-14-pro")
                for item in client.get(f"/api/v1/pricing/products/{slug}/").json()}
    assert {"in_stock", "on_order"} <= statuses

    quote = client.post(
        "/api/v1/orders/quote/", {"items": [{"sku": "IP16P-256-BLK", "qty": 1}]}, content_type="application/json"
    ).json()
    assert quote["lines"][0]["gift_options"], "к iPhone должен находиться хотя бы один подарок"

    accessories = client.get("/api/v1/catalog/products/galaxy-s25-ultra/accessories/").json()["results"]
    assert {"case-galaxy-s25-ultra", "charger-samsung-45w"} <= {a["slug"] for a in accessories}


def test_seed_demo_is_idempotent():
    seed()
    counts = (ProductModel.objects.count(), Variant.objects.count(), InventoryUnit.objects.count())

    seed()

    assert (ProductModel.objects.count(), Variant.objects.count(), InventoryUnit.objects.count()) == counts
