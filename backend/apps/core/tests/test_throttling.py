import pytest
from django.core.cache import cache

from apps.core.throttling import ClientRateThrottle, client_ident

pytestmark = pytest.mark.django_db

SUGGEST = "/api/v1/catalog/search/suggest/"
CATEGORIES = "/api/v1/catalog/categories/"


@pytest.fixture(autouse=True)
def low_limits(monkeypatch):
    cache.clear()
    monkeypatch.setattr(ClientRateThrottle, "THROTTLE_RATES", {"anon": "3/min", "search": "2/min"})
    yield
    cache.clear()


class FakeRequest:
    def __init__(self, remote, forwarded=None):
        self.META = {"REMOTE_ADDR": remote}
        if forwarded:
            self.META["HTTP_X_FORWARDED_FOR"] = forwarded


@pytest.mark.parametrize(
    "remote, forwarded, expected",
    [
        ("8.8.8.8", None, "8.8.8.8"),  # напрямую из интернета
        ("8.8.8.8", "1.1.1.1", "8.8.8.8"),  # чужой прокси не может подставить адрес
        ("127.0.0.1", "6.6.6.6, 9.9.9.9", "9.9.9.9"),  # адрес, который дописал наш nginx
        ("127.0.0.1", None, None),  # серверная отрисовка витрины — без лимита
    ],
)
def test_client_ident(remote, forwarded, expected):
    assert client_ident(FakeRequest(remote, forwarded)) == expected


def get(client, path, **headers):
    return client.get(path, {"q": "iphone"}, **headers).status_code


def test_public_endpoint_is_limited_per_client(client):
    statuses = [get(client, CATEGORIES, REMOTE_ADDR="8.8.8.8") for _ in range(4)]

    assert statuses == [200, 200, 200, 429]
    assert get(client, CATEGORIES, REMOTE_ADDR="8.8.4.4") == 200


def test_search_has_its_own_stricter_limit(client):
    statuses = [get(client, SUGGEST, REMOTE_ADDR="8.8.8.8") for _ in range(3)]

    assert statuses == [200, 200, 429]


def test_visitors_behind_the_proxy_are_counted_separately(client):
    for _ in range(3):
        get(client, CATEGORIES, HTTP_X_FORWARDED_FOR="1.1.1.1")

    assert get(client, CATEGORIES, HTTP_X_FORWARDED_FOR="1.1.1.1") == 429
    assert get(client, CATEGORIES, HTTP_X_FORWARDED_FOR="2.2.2.2") == 200


def test_server_side_rendering_is_not_limited(client):
    assert {get(client, CATEGORIES) for _ in range(10)} == {200}
