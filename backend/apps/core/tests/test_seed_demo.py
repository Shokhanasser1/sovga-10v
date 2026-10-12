import pytest
from django.core.management import call_command
from django.db.models import Count, Q

from apps.catalog.models import Category, ProductModel, Status, Variant
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
    assert search_products("айфон 16 про")[0] == iphone

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


DEMO_CATEGORIES = {
    "smartphones", "tablets", "smartwatches", "headphones", "cases", "screen-protectors", "chargers", "power-banks",
}


def test_seed_demo_fills_every_category_with_described_products():
    seed()

    active = Q(product_models__status=Status.ACTIVE)
    counts = dict(Category.objects.annotate(n=Count("product_models", filter=active)).values_list("slug", "n"))
    assert DEMO_CATEGORIES <= counts.keys()
    assert all(counts[slug] >= 3 for slug in DEMO_CATEGORIES), counts
    products = ProductModel.objects.filter(status=Status.ACTIVE).select_related("category")
    assert products.count() >= 40
    for product in products:
        assert product.description_ru and product.description_uz, f"{product.slug}: нет описания"
        assert product.price_from_uzs, f"{product.slug}: нет цены"
        product.clean()  # характеристики совпадают с атрибутами категории
        for variant in product.variants.all():
            variant.clean()


def test_seed_demo_links_accessories_and_gifts_for_new_models(client):
    seed()

    accessories = client.get("/api/v1/catalog/products/iphone-17-pro/accessories/").json()["results"]
    assert {"case-iphone-17-pro", "glass-iphone-17-pro"} <= {a["slug"] for a in accessories}
    quote = client.post(
        "/api/v1/orders/quote/", {"items": [{"sku": "IP17P-256-ORG", "qty": 1}]}, content_type="application/json"
    ).json()
    assert quote["lines"][0]["gift_options"]


def test_seed_demo_search_understands_new_brands_and_categories():
    seed()

    assert search_products("хонор 400")[0].slug == "honor-400"
    assert {p.category.slug for p in search_products("эпл вотч")} == {"smartwatches"}
    assert {p.category.slug for p in search_products("павербанк")} == {"power-banks"}
    assert {p.category.slug for p in search_products("стекло")} == {"screen-protectors"}
