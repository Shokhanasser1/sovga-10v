import pytest
from django.test import Client

from apps.customers.services import customer_for_phone
from apps.orders.models import Order
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db
S = Order.Status


@pytest.fixture
def demo(settings):
    settings.DEMO_MODE = True
    settings.SITE_URL = "http://localhost:3000"
    for name in ("PAYME_MERCHANT_ID", "PAYME_KEY", "CLICK_SERVICE_ID", "CLICK_MERCHANT_ID", "CLICK_SECRET_KEY"):
        setattr(settings, name, "")


def browser(user=None):
    client = Client(enforce_csrf_checks=True)
    if user is not None:
        client.force_login(user)
    client.get("/api/v1/auth/me/")
    return client


def demo_url(provider, order):
    return f"/api/v1/payments/demo/{provider}/{order.number}/"


def act(client, provider, order, action):
    return client.post(
        demo_url(provider, order) + "?lang=uz", {"action": action, "csrfmiddlewaretoken": client.cookies["csrftoken"].value}
    )


def test_demo_flag(demo):
    assert Client().get("/api/v1/demo/").json() == {"demo": True}


def test_without_demo_nothing_is_simulated(order, settings):
    settings.DEMO_MODE = False
    settings.PAYME_KEY = ""
    client = browser(order.customer.user)

    assert client.get(f"/api/v1/orders/{order.number}/").json()["pay_providers"] == []
    assert client.get(demo_url("payme", order)).status_code == 404
    assert Client().get("/api/v1/demo/").json() == {"demo": False}


def test_demo_offers_both_providers_through_the_simulator(demo, order):
    client = browser(order.customer.user)
    assert client.get(f"/api/v1/orders/{order.number}/").json()["pay_providers"] == ["payme", "click"]

    response = client.post(
        f"/api/v1/orders/{order.number}/pay/", {"provider": "click", "lang": "uz"}, content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )

    assert response.json()["url"] == f"http://testserver{demo_url('click', order)}?lang=uz"


def test_real_keys_win_over_the_simulator(demo, order, settings):
    settings.PAYME_MERCHANT_ID, settings.PAYME_KEY = "m", "k"
    client = browser(order.customer.user)

    response = client.post(
        f"/api/v1/orders/{order.number}/pay/", {"provider": "payme", "lang": "ru"}, content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )

    assert response.json()["url"].startswith(settings.PAYME_CHECKOUT_URL)
    assert browser(order.customer.user).get(demo_url("payme", order)).status_code == 404


def test_page_is_only_for_the_owner(demo, order):
    page = browser(order.customer.user).get(demo_url("payme", order))
    assert page.status_code == 200
    text = page.content.decode()
    assert "Учебная оплата" in text and order.number in text and "не списываются" in text

    assert browser().get(demo_url("payme", order)).status_code == 404
    assert browser(customer_for_phone("+998935554433").user).get(demo_url("payme", order)).status_code == 404
    assert browser(order.customer.user).get(demo_url("bitcoin", order)).status_code == 404


@pytest.mark.parametrize("provider", ["payme", "click"])
def test_simulated_payment_goes_through_the_provider_protocol(demo, order, provider):
    client = browser(order.customer.user)

    response = act(client, provider, order, "pay")

    assert response.status_code == 302
    assert response["Location"] == f"http://localhost:3000/uz/orders/{order.number}"
    order.refresh_from_db()
    assert order.status == S.PAID
    payment = Payment.objects.get(order=order)
    assert (payment.provider, payment.state) == (provider, Payment.State.PAID)


@pytest.mark.parametrize("provider", ["payme", "click"])
def test_declined_payment_lets_the_customer_try_again(demo, order, provider):
    act(browser(order.customer.user), provider, order, "decline")

    order.refresh_from_db()
    assert order.status == S.CONFIRMED
    assert Payment.objects.get(order=order).state == Payment.State.CANCELLED


def test_provider_refund(demo, order):
    client = browser(order.customer.user)
    act(client, "payme", order, "pay")

    act(client, "payme", order, "refund")

    order.refresh_from_db()
    assert order.status == S.CANCELLED
    assert Payment.objects.get(order=order).state == Payment.State.REFUNDED


def test_actions_need_csrf(demo, order):
    client = browser(order.customer.user)

    assert client.post(demo_url("payme", order), {"action": "pay"}).status_code == 403
    order.refresh_from_db()
    assert order.status == S.CONFIRMED


def test_paying_twice_is_refused_by_the_protocol(demo, order):
    client = browser(order.customer.user)
    act(client, "payme", order, "pay")

    page = client.get(demo_url("click", order)).content.decode()

    assert "уже оплачен" in page or "нельзя оплатить" in page
