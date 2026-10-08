import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.customers.services import customer_for_phone
from apps.orders.models import Order
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, create_order

pytestmark = pytest.mark.django_db

BASE = "/api/v1/orders"
PHONE_SKU = "IP16P-256-B"
ORDER = {
    "items": [{"sku": PHONE_SKU, "qty": 1, "gift_sku": "CASE-1"}],
    "payment_method": "card",
    "address": {"text": "Ташкент, Юнусабад 4-12", "landmark": "напротив школы №110"},
    "comment": "Позвонить за час",
}


@pytest.fixture
def customer():
    return customer_for_phone("+998901234567")


def browser(user=None):
    client = Client(enforce_csrf_checks=True, HTTP_ORIGIN="http://localhost:3000")
    if user:
        client.force_login(user)
    client.get("/api/v1/auth/me/")
    return client


def post(client, path, data):
    return client.post(path, data, content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)


def test_quote_is_public(shop):
    response = post(browser(), f"{BASE}/quote/", {"items": [{"sku": PHONE_SKU, "qty": 2}], "payment_method": "card"})

    body = response.json()
    assert response.status_code == 200
    assert body["total_uzs"] == 28_160_000 and body["can_order"]
    [line] = body["lines"]
    assert line["gift_budget_uzs"] == 128_000
    assert [option["sku"] for option in line["gift_options"]] == ["CASE-1"]
    assert "cost_usd" not in str(body)


def test_quote_validates_payload(shop):
    response = post(browser(), f"{BASE}/quote/", {"items": [{"sku": PHONE_SKU, "qty": 0}]})

    assert response.status_code == 400


def test_order_requires_login(shop):
    assert post(browser(), f"{BASE}/", ORDER).status_code == 403


def test_order_requires_csrf(shop, customer):
    client = browser(customer.user)

    response = client.post(f"{BASE}/", ORDER, content_type="application/json")

    assert response.status_code == 403
    assert not Order.objects.exists()


def test_create_and_read_order(shop, customer):
    client = browser(customer.user)

    response = post(client, f"{BASE}/", ORDER)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed" and body["can_cancel"]
    assert [(line["sku"], line["is_gift"]) for line in body["lines"]] == [(PHONE_SKU, False), ("CASE-1", True)]
    assert client.get(f"{BASE}/{body['number']}/").json()["number"] == body["number"]
    assert [o["number"] for o in client.get(f"{BASE}/").json()] == [body["number"]]


def test_only_card_payment_for_now(shop, customer):
    response = post(browser(customer.user), f"{BASE}/", {**ORDER, "payment_method": "installment"})

    assert response.status_code == 400


def test_invalid_cart_explains_the_problem(shop, customer):
    bad = {**ORDER, "items": [{"sku": PHONE_SKU, "qty": 1, "gift_sku": "CASE-PREMIUM"}]}

    response = post(browser(customer.user), f"{BASE}/", bad)

    assert response.status_code == 400
    assert "подарок" in response.json()["detail"]


def test_other_customers_orders_are_hidden(shop, customer):
    order = create_order(customer, [CartItem(PHONE_SKU, 1)], "card", DeliveryAddress("Ташкент"), "", timezone.now())
    stranger = customer_for_phone("+998935554433")
    client = browser(stranger.user)

    assert client.get(f"{BASE}/{order.number}/").status_code == 404
    assert client.get(f"{BASE}/").json() == []
    assert post(client, f"{BASE}/{order.number}/cancel/", {}).status_code == 404


def test_customer_cancels_own_order(shop, customer):
    order = create_order(customer, [CartItem(PHONE_SKU, 1)], "card", DeliveryAddress("Ташкент"), "", timezone.now())

    response = post(browser(customer.user), f"{BASE}/{order.number}/cancel/", {})

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_paid_order_is_not_cancelled_by_customer(shop, customer):
    order = create_order(customer, [CartItem(PHONE_SKU, 1)], "card", DeliveryAddress("Ташкент"), "", timezone.now())
    Order.objects.filter(pk=order.pk).update(status=Order.Status.PAID)

    response = post(browser(customer.user), f"{BASE}/{order.number}/cancel/", {})

    assert response.status_code == 400


def test_staff_without_customer_profile_cannot_order(shop):
    staff = get_user_model().objects.create_user(username="anna", password="x", is_staff=True)

    assert post(browser(staff), f"{BASE}/", ORDER).status_code == 403


def test_basic_auth_is_disabled(shop):
    get_user_model().objects.create_user(username="anna", password="secret-pass", is_staff=True)
    client = Client(HTTP_AUTHORIZATION="Basic YW5uYTpzZWNyZXQtcGFzcw==")

    assert client.get(f"{BASE}/").status_code == 403
