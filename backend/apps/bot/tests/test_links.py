from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.bot.links import LINK_TTL, customer_link, redeem, supplier_link
from apps.bot.models import TelegramLink
from apps.customers.services import customer_for_phone

from .conftest import NOW, start_payload

pytestmark = pytest.mark.django_db


def test_customer_link_binds_the_chat(bot, customer):
    url = customer_link(customer, NOW)

    assert url.startswith("https://t.me/sovga_test_bot?start=c_")
    link = redeem(start_payload(url), 555, NOW)
    customer.refresh_from_db()
    assert link.customer == customer
    assert customer.telegram_chat_id == 555


def test_code_is_long_and_single_use(bot, customer):
    payload = start_payload(customer_link(customer, NOW))
    assert len(payload) >= 2 + 22  # 128 бит случайности

    redeem(payload, 555, NOW)

    assert redeem(payload, 777, NOW) is None
    customer.refresh_from_db()
    assert customer.telegram_chat_id == 555


def test_code_expires(bot, customer):
    payload = start_payload(customer_link(customer, NOW))

    assert redeem(payload, 555, NOW + LINK_TTL + timedelta(seconds=1)) is None


def test_new_link_replaces_the_unused_one(bot, customer):
    old = start_payload(customer_link(customer, NOW))
    customer_link(customer, NOW)

    assert redeem(old, 555, NOW) is None
    assert TelegramLink.objects.filter(customer=customer).count() == 1


@pytest.mark.parametrize("payload", ["", "c_", "c", "x_abc", "garbage", "c_" + "a" * 22])
def test_unknown_codes(bot, customer, payload):
    customer_link(customer, NOW)

    assert redeem(payload, 1, NOW) is None


def test_kind_must_match(bot, customer):
    code = start_payload(customer_link(customer, NOW)).split("_", 1)[1]

    assert redeem(f"s_{code}", 1, NOW) is None


def test_chat_belongs_to_one_customer(bot, customer):
    other = customer_for_phone("+998935554433")
    redeem(start_payload(customer_link(other, NOW)), 555, NOW)

    redeem(start_payload(customer_link(customer, NOW)), 555, NOW)

    other.refresh_from_db()
    assert other.telegram_chat_id is None


def test_supplier_link(bot, make_supplier):
    supplier = make_supplier("Опт", connector_type="telegram")

    url = supplier_link(supplier, NOW)
    redeem(start_payload(url), 999, NOW)

    assert url.startswith("https://t.me/sovga_test_bot?start=s_")
    supplier.refresh_from_db()
    assert supplier.telegram_chat_id == 999


def browser(user=None):
    client = Client(enforce_csrf_checks=True, HTTP_ORIGIN="http://localhost:3000")
    if user is not None:
        client.force_login(user)
    client.get("/api/v1/auth/me/")
    return client


def ask_link(client, lang="uz", csrf=True):
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}
    return client.post("/api/v1/bot/link/", {"lang": lang}, content_type="application/json", **headers)


def test_customer_gets_a_link_and_language_is_saved(bot, customer):
    response = ask_link(browser(customer.user), "uz")

    assert response.status_code == 200
    assert response.json()["url"].startswith("https://t.me/sovga_test_bot?start=c_")
    customer.refresh_from_db()
    assert customer.language == "uz"


def test_link_needs_a_customer(bot):
    assert ask_link(browser()).status_code == 403
    staff = get_user_model().objects.create_user("manager", password="x", is_staff=True)
    assert ask_link(browser(staff)).status_code == 403


def test_link_needs_csrf(bot, customer):
    assert ask_link(browser(customer.user), csrf=False).status_code == 403


def test_unknown_language(bot, customer):
    assert ask_link(browser(customer.user), "en").status_code == 400


def test_without_bot_link_is_unavailable(bot, settings, customer):
    settings.TELEGRAM_BOT_USERNAME = ""

    assert ask_link(browser(customer.user)).status_code == 503


def test_admin_gives_a_supplier_link(bot, admin_client, make_supplier):
    supplier = make_supplier("Опт", connector_type="telegram")

    response = admin_client.post(
        "/admin/sourcing/supplier/", {"action": "bot_link_action", "_selected_action": [supplier.pk]}, follow=True
    )

    assert "https://t.me/sovga_test_bot?start=s_" in response.content.decode()


def test_order_page_offers_telegram(bot, settings, shop):
    from apps.orders.quote import CartItem
    from apps.orders.serializers import order_payload
    from apps.orders.services import DeliveryAddress, create_order

    customer = customer_for_phone("+998901234567")
    order = create_order(customer, [CartItem("IP16P-256-B", 1)], "card", DeliveryAddress("Ташкент"), "", NOW)
    assert order_payload(order)["telegram"] == "available"

    redeem(start_payload(customer_link(customer, NOW)), 555, NOW)
    order.customer.refresh_from_db()
    assert order_payload(order)["telegram"] == "linked"

    settings.TELEGRAM_BOT_TOKEN = ""
    order.customer.telegram_chat_id = None
    assert order_payload(order)["telegram"] == "off"
