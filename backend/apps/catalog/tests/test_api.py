import pytest

from apps.catalog.models import AccessoryCompat, Brand, Category, ProductModel, Status

pytestmark = pytest.mark.django_db

BASE = "/api/v1/catalog"


@pytest.fixture
def catalog(iphone, phones, make_variant):
    make_variant(iphone, "IP-256-B", {"storage_gb": 256, "color": "black"},
                 attributes={"weight_g": 199}, status=Status.ACTIVE).save()
    make_variant(iphone, "IP-512-W", {"storage_gb": 512, "color": "white"},
                 attributes={"weight_g": 199}, status=Status.DRAFT).save()
    return iphone


def test_categories_are_public(phones, client):
    response = client.get(f"{BASE}/categories/")

    assert response.status_code == 200
    assert [c["slug"] for c in response.json()] == ["phones"]


def test_product_list_includes_subcategories_and_hides_drafts(catalog, phones, apple, client):
    flagships = Category.objects.create(slug="flagships", name_ru="Флагманы", name_uz="Flagmanlar", parent=phones)
    ProductModel.objects.create(category=flagships, brand=apple, slug="iphone-17-pro",
                                name_ru="iPhone 17 Pro", name_uz="iPhone 17 Pro", status=Status.ACTIVE)
    ProductModel.objects.create(category=phones, brand=apple, slug="draft-phone",
                                name_ru="Черновик", name_uz="Qoralama")

    response = client.get(f"{BASE}/products/", {"category": "phones"})

    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()["results"]]
    assert slugs == ["iphone-16-pro", "iphone-17-pro"]


def test_product_detail_shows_active_variants_without_fiscal_codes(catalog, client):
    response = client.get(f"{BASE}/products/iphone-16-pro/")

    assert response.status_code == 200
    body = response.json()
    assert [v["sku"] for v in body["variants"]] == ["IP-256-B"]
    assert "mxik_code" not in body["variants"][0]
    assert body["brand"]["name"] == "Apple"


def test_unknown_product_is_404(client, db):
    assert client.get(f"{BASE}/products/nope/").status_code == 404


def test_accessories_endpoint(catalog, apple, client):
    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    case = ProductModel.objects.create(category=cases, brand=apple, slug="case-16-pro",
                                       name_ru="Чехол 16 Pro", name_uz="G'ilof 16 Pro",
                                       is_accessory=True, status=Status.ACTIVE)
    AccessoryCompat.objects.create(accessory=case, device=catalog)

    response = client.get(f"{BASE}/products/iphone-16-pro/accessories/")

    assert [p["slug"] for p in response.json()["results"]] == ["case-16-pro"]


def test_compare_returns_rows_with_best(catalog, phones, make_variant, client):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(category=phones, brand=samsung, slug="galaxy-s26",
                                         name_ru="Galaxy S26", name_uz="Galaxy S26",
                                         attributes={"battery_mah": 5000}, status=Status.ACTIVE)
    make_variant(galaxy, "S26-256", {"storage_gb": 256, "color": "black"},
                 attributes={"weight_g": 220}, status=Status.ACTIVE).save()

    response = client.get(f"{BASE}/compare/", {"skus": "IP-256-B,S26-256"})

    assert response.status_code == 200
    rows = {row["code"]: row for row in response.json()}
    assert rows["battery_mah"]["best"] == [1]
    assert rows["weight_g"]["best"] == [0]


@pytest.mark.parametrize("skus", ["IP-256-B", "IP-256-B,NOPE", "A,B,C,D,E"])
def test_compare_rejects_bad_requests(catalog, client, skus):
    assert client.get(f"{BASE}/compare/", {"skus": skus}).status_code == 400


def test_api_is_read_only(catalog, client):
    assert client.post(f"{BASE}/products/", {}).status_code in (403, 405)
