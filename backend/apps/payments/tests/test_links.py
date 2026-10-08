import base64
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import Client

from apps.customers.services import customer_for_phone
from apps.notifications.outbox import deliver_pending
from apps.orders.models import Order
from apps.orders.services import expire_orders
from apps.payments.services import PAYMENT_WINDOW, confirm_payment, start_payment

from .conftest import NOW

pytestmark = pytest.mark.django_db
S = Order.Status


@pytest.fixture
def configured(settings):
    settings.PAYME_MERCHANT_ID = "merchant-1"
    settings.PAYME_KEY = "k"
    settings.PAYME_CHECKOUT_URL = "https://checkout.paycom.uz"
    settings.CLICK_SERVICE_ID = "111"
    settings.CLICK_MERCHANT_ID = "222"
    settings.CLICK_SECRET_KEY = "s"
    settings.SITE_URL = "https://sovga.uz"


def browser(user):
    client = Client(enforce_csrf_checks=True, HTTP_ORIGIN="http://localhost:3000")
    client.force_login(user)
    client.get("/api/v1/auth/me/")
    return client


def pay(client, order, provider, lang="ru"):
    return client.post(
        f"/api/v1/orders/{order.number}/pay/", {"provider": provider, "lang": lang},
        content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )


def test_payme_link(configured, order):
    response = pay(browser(order.customer.user), order, "payme", lang="uz")

    url = response.json()["url"]
    assert url.startswith("https://checkout.paycom.uz/")
    decoded = base64.b64decode(url.rsplit("/", 1)[1]).decode()
    assert decoded == (
        f"m=merchant-1;ac.order_id={order.number};a={order.total_uzs * 100};"
        f"c=https://sovga.uz/uz/orders/{order.number};l=uz"
    )


def test_click_link(configured, order):
    url = pay(browser(order.customer.user), order, "click").json()["url"]

    query = parse_qs(urlparse(url).query)
    assert url.startswith("https://my.click.uz/services/pay?")
    assert query["service_id"] == ["111"] and query["merchant_id"] == ["222"]
    assert query["amount"] == [str(order.total_uzs)] and query["transaction_param"] == [order.number]
    assert query["return_url"] == [f"https://sovga.uz/ru/orders/{order.number}"]


def test_without_settings_payment_is_unavailable(order, settings):
    settings.PAYME_MERCHANT_ID = ""

    response = pay(browser(order.customer.user), order, "payme")

    assert response.status_code == 503


@pytest.mark.parametrize("provider", ["bitcoin", ""])
def test_unknown_provider(configured, order, provider):
    assert pay(browser(order.customer.user), order, provider).status_code == 400


def test_only_own_payable_orders(configured, order):
    stranger = customer_for_phone("+998935554433")
    assert pay(browser(stranger.user), order, "payme").status_code == 404

    Order.objects.filter(pk=order.pk).update(status=S.CANCELLED)
    assert pay(browser(order.customer.user), order, "payme").status_code == 400


def test_order_payload_lists_available_providers(configured, order, settings):
    settings.CLICK_SECRET_KEY = ""
    client = browser(order.customer.user)

    body = client.get(f"/api/v1/orders/{order.number}/").json()

    assert body["can_pay"] is True
    assert body["pay_providers"] == ["payme"]


def test_unpaid_payment_window_expires(order):
    start_payment(order, NOW, actor="payme")

    assert expire_orders(NOW + PAYMENT_WINDOW + timedelta(seconds=1)) == 1
    order.refresh_from_db()
    assert order.status == S.CANCELLED


def test_paid_order_notifies_managers(order, monkeypatch):
    sent = []
    monkeypatch.setattr("apps.payments.handlers.notify_managers", sent.append)
    start_payment(order, NOW, actor="payme")
    confirm_payment(order, NOW, actor="payme", provider="Payme")

    deliver_pending(NOW)

    assert any(order.number in text and "оплачен через Payme" in text for text in sent)


def test_expiry_skips_an_order_paid_meanwhile(order):
    from apps.orders.services import expire_if_still_due

    start_payment(order, NOW, actor="payme")
    Order.objects.filter(pk=order.pk).update(status=S.PAID)

    assert expire_if_still_due(order.pk, S.AWAITING_PAYMENT, NOW + PAYMENT_WINDOW * 2) is False
    order.refresh_from_db()
    assert order.status == S.PAID


def test_expiry_skips_a_payment_window_extended_meanwhile(order):
    from apps.orders.services import expire_if_still_due

    start_payment(order, NOW, actor="payme")
    start_payment(order, NOW + PAYMENT_WINDOW, actor="payme")  # новая транзакция продлила окно

    assert expire_if_still_due(order.pk, S.AWAITING_PAYMENT, NOW + PAYMENT_WINDOW + timedelta(minutes=1)) is False
    order.refresh_from_db()
    assert order.status == S.AWAITING_PAYMENT
