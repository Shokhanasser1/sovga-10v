import pytest

from apps.catalog.models import AttributeDefinition, Brand, ProductModel, Status

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/catalog/products/"
FACETS = "/api/v1/catalog/facets/"


@pytest.fixture
def shop(iphone, phones, make_variant):
    AttributeDefinition.objects.filter(category=phones, code__in=["storage_gb", "color", "battery_mah"]).update(
        is_facet=True
    )
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(category=phones, brand=samsung, slug="galaxy-s25-ultra",
                                         name_ru="Galaxy S25 Ultra", name_uz="Galaxy S25 Ultra",
                                         attributes={"battery_mah": 5000}, status=Status.ACTIVE)
    for product, sku, storage, color, status in [
        (iphone, "IP-256-B", 256, "black", Status.ACTIVE),
        (iphone, "IP-512-W", 512, "white", Status.ACTIVE),
        (galaxy, "S25-256-W", 256, "white", Status.ACTIVE),
        (galaxy, "S25-1024-B", 1024, "black", Status.DRAFT),
    ]:
        make_variant(product, sku, {"storage_gb": storage, "color": color}, status=status).save()
    ProductModel.objects.filter(pk=iphone.pk).update(price_from_uzs=14_080_000, is_available=True)
    ProductModel.objects.filter(pk=galaxy.pk).update(price_from_uzs=12_000_000, is_available=False)
    return {"iphone": iphone, "galaxy": galaxy}


def listed(client, **params):
    response = client.get(PRODUCTS, params)
    assert response.status_code == 200
    return [item["slug"] for item in response.json()["results"]]


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"f.storage_gb": "512"}, ["iphone-16-pro"]),
        ({"f.storage_gb": "1024"}, []),
        ({"f.color": "white"}, ["galaxy-s25-ultra", "iphone-16-pro"]),
        ({"f.battery_mah": "5000"}, ["galaxy-s25-ultra"]),
        ({"f.storage_gb": "256,512", "f.color": "black"}, ["iphone-16-pro"]),
        ({"brand": "samsung"}, ["galaxy-s25-ultra"]),
        ({"f.unknown": "1"}, ["galaxy-s25-ultra", "iphone-16-pro"]),
        ({"f.storage_gb": "abc"}, ["galaxy-s25-ultra", "iphone-16-pro"]),
        ({"price_min": "13000000"}, ["iphone-16-pro"]),
        ({"price_max": "13000000"}, ["galaxy-s25-ultra"]),
        ({"price_min": "много"}, ["galaxy-s25-ultra", "iphone-16-pro"]),
        ({"available": "1"}, ["iphone-16-pro"]),
        ({"q": "самсунг"}, ["galaxy-s25-ultra"]),
        ({"q": "nothing-like-this"}, []),
    ],
)
def test_filters(shop, client, params, expected):
    assert sorted(listed(client, category="phones", **params)) == expected


def test_available_products_come_first(shop, client):
    assert listed(client, sort="price_asc") == ["iphone-16-pro", "galaxy-s25-ultra"]


def test_price_sorting(shop, client):
    ProductModel.objects.update(is_available=True)

    assert listed(client, sort="price_asc") == ["galaxy-s25-ultra", "iphone-16-pro"]
    assert listed(client, sort="price_desc") == ["iphone-16-pro", "galaxy-s25-ultra"]


def test_search_relevance_order(shop, iphone, apple, phones, client):
    ProductModel.objects.create(category=phones, brand=apple, slug="phone-iphone-se",
                                name_ru="Смартфон Apple iPhone SE", name_uz="Apple iPhone SE",
                                status=Status.ACTIVE, is_available=True)

    assert listed(client, q="iphone") == ["iphone-16-pro", "phone-iphone-se"]


def test_listing_shows_price_from_and_availability(shop, client):
    item = next(i for i in client.get(PRODUCTS).json()["results"] if i["slug"] == "iphone-16-pro")

    assert (item["price_from_uzs"], item["is_available"]) == (14_080_000, True)


def test_facets(shop, client):
    body = client.get(FACETS, {"category": "phones"}).json()

    assert body["brands"] == [
        {"slug": "apple", "name": "Apple", "count": 1},
        {"slug": "samsung", "name": "Samsung", "count": 1},
    ]
    facets = {a["code"]: a["values"] for a in body["attributes"]}
    assert facets["storage_gb"] == [{"value": 256, "count": 2}, {"value": 512, "count": 1}]
    assert facets["color"] == [{"value": "black", "count": 1}, {"value": "white", "count": 2}]
    assert facets["battery_mah"] == [{"value": 3582, "count": 1}, {"value": 5000, "count": 1}]
    assert "weight_g" not in facets
    assert body["price"] == {"min": 12_000_000, "max": 14_080_000}


def test_facets_respect_search_query(shop, client):
    body = client.get(FACETS, {"category": "phones", "q": "samsung"}).json()

    assert [b["slug"] for b in body["brands"]] == ["samsung"]


def test_facets_without_category_have_only_brands_and_price(shop, client):
    body = client.get(FACETS).json()

    assert body["attributes"] == []
    assert len(body["brands"]) == 2
