import pytest

pytestmark = pytest.mark.django_db

URL = "/api/v1/catalog/categories/"


def test_storefront_origin_may_read_the_api(client):
    response = client.get(URL, HTTP_ORIGIN="http://localhost:3000")

    assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_other_origins_are_not_allowed(client):
    response = client.get(URL, HTTP_ORIGIN="https://evil.example")

    assert "Access-Control-Allow-Origin" not in response
