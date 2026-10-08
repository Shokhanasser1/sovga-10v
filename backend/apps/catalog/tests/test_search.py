import pytest
from django.core.management import call_command

from apps.catalog.models import Brand, Category, ProductModel, Status
from apps.catalog.search import search_products, suggest

pytestmark = pytest.mark.django_db

BASE = "/api/v1/catalog"


@pytest.fixture
def shop(iphone, phones, apple):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(category=phones, brand=samsung, slug="galaxy-s25-ultra",
                                         name_ru="Galaxy S25 Ultra", name_uz="Galaxy S25 Ultra",
                                         status=Status.ACTIVE)
    ProductModel.objects.create(category=phones, brand=apple, slug="iphone-17-pro",
                                name_ru="iPhone 17 Pro", name_uz="iPhone 17 Pro")
    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    case = ProductModel.objects.create(category=cases, brand=apple, slug="case-iphone-16-pro",
                                       name_ru="Чехол для iPhone 16 Pro", name_uz="iPhone 16 Pro uchun g'ilof",
                                       is_accessory=True, status=Status.ACTIVE)
    return {"iphone": iphone, "galaxy": galaxy, "case": case, "cases": cases}


def slugs(products):
    return [product.slug for product in products]


def test_russian_brand_name_finds_iphone_first(shop):
    assert slugs(search_products("айфон 16")) == ["iphone-16-pro", "case-iphone-16-pro"]


def test_latin_misspelling_from_synonyms(shop):
    assert "iphone-16-pro" in slugs(search_products("aypon"))


def test_cyrillic_brand_and_model(shop):
    assert slugs(search_products("самсунг галакси")) == ["galaxy-s25-ultra"]


def test_glued_model_number(shop):
    assert slugs(search_products("galaxy s25")) == ["galaxy-s25-ultra"]


def test_typo_falls_back_to_fuzzy(shop):
    assert slugs(search_products("iphnoe"))[0] == "iphone-16-pro"


def test_category_words_are_searchable(shop):
    assert set(slugs(search_products("смартфон"))) == {"iphone-16-pro", "galaxy-s25-ultra"}


def test_uzbek_latin_with_apostrophe(shop):
    assert slugs(search_products("g'ilof")) == ["case-iphone-16-pro"]


def test_drafts_and_empty_queries(shop):
    assert search_products("iphone 17") == []
    assert search_products("  !!! ") == []


def test_suggest_returns_products_and_categories(shop):
    result = suggest("чехол")

    assert slugs(result["products"]) == ["case-iphone-16-pro"]
    assert [c.slug for c in result["categories"]] == ["cases"]


def test_suggest_endpoint(shop, client):
    response = client.get(f"{BASE}/search/suggest/", {"q": "айфон"})

    assert response.status_code == 200
    body = response.json()
    assert body["products"][0]["slug"] == "iphone-16-pro"
    assert body["categories"] == []


def test_rebuild_index_picks_up_renamed_brand(shop):
    Brand.objects.filter(slug="samsung").update(name="Samsung Electronics")

    call_command("rebuild_search_index")

    assert slugs(search_products("electronics")) == ["galaxy-s25-ultra"]
