import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.bot.demo import DEMO_MANAGER_CHAT, customer_chat, supplier_chat
from apps.bot.models import DemoMessage
from apps.notifications.telegram import notify_managers, send_message
from apps.orders.models import Order, SupplierRequest
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, create_order
from apps.orders.tests.conftest import stock
from apps.sourcing.models import Offer, Supplier

from .conftest import NOW

pytestmark = pytest.mark.django_db
SIMULATOR = reverse("admin:bot_demomessage_changelist")


@pytest.fixture
def demo(settings):
    settings.DEMO_MODE = True
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.TELEGRAM_BOT_USERNAME = ""
    settings.MANAGER_CHAT_IDS = []


def test_messages_are_stored_instead_of_sent(demo):
    markup = {"inline_keyboard": [[{"text": "Да", "callback_data": "x"}]]}

    message_id = send_message(42, "Привет", reply_markup=markup)

    message = DemoMessage.objects.get()
    assert (message.pk, message.chat_id, message.text, message.reply_markup) == (message_id, 42, "Привет", markup)
    assert message.direction == DemoMessage.Direction.OUT


def test_managers_get_a_learning_chat(demo):
    assert notify_managers("Новый заказ") == 1

    assert DemoMessage.objects.get().chat_id == DEMO_MANAGER_CHAT


def test_real_token_wins(demo, settings, monkeypatch):
    settings.TELEGRAM_BOT_TOKEN = "123:real"
    posted = []

    class Ok:
        def json(self):
            return {"ok": True, "result": {"message_id": 7}}

    send_message(42, "x", http_post=lambda url, **kw: posted.append(url) or Ok())

    assert posted and not DemoMessage.objects.exists()


def test_customer_link_connects_a_learning_chat(demo, customer):
    client = Client(enforce_csrf_checks=True)
    client.force_login(customer.user)
    client.get("/api/v1/auth/me/")

    response = client.post("/api/v1/bot/link/", {"lang": "ru"}, content_type="application/json",
                           HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)

    assert response.json() == {"url": ""}
    customer.refresh_from_db()
    assert customer.telegram_chat_id == customer_chat(customer)


@pytest.fixture
def supplier_order(demo, shop, customer):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    supplier = Supplier.objects.create(name="Опт Чиланзар", connector_type=Supplier.Connector.TELEGRAM)
    stock(shop["phone"], 5, supplier=supplier)
    return supplier


def test_supplier_answers_from_the_simulator(admin_client, supplier_order, customer):
    supplier = supplier_order
    admin_client.post(SIMULATOR, {"action": "link_supplier", "supplier": supplier.pk})
    supplier.refresh_from_db()
    assert supplier.telegram_chat_id == supplier_chat(supplier)
    order = create_order(customer, [CartItem("IP16P-256-B", 1)], "card", DeliveryAddress("Ташкент"), "", NOW)

    page = admin_client.get(SIMULATOR, {"chat": supplier.telegram_chat_id}).content.decode()  # outbox доставлен

    assert order.number in page and "✅ Есть" in page
    request = SupplierRequest.objects.get(order=order)
    message = DemoMessage.objects.get(chat_id=supplier.telegram_chat_id, reply_markup__isnull=False)
    admin_client.post(SIMULATOR, {"action": "press", "chat": supplier.telegram_chat_id, "message": message.pk,
                                  "data": f"sr:{request.pk}:yes"})
    order.refresh_from_db()
    assert order.status == Order.Status.CONFIRMED
    message.refresh_from_db()
    assert message.reply_markup is None and "заказ подтверждён" in message.text


def test_typing_as_a_chat(admin_client, demo):
    response = admin_client.post(SIMULATOR, {"action": "say", "chat": 555, "text": "/id"}, follow=True)

    texts = list(DemoMessage.objects.filter(chat_id=555).order_by("pk").values_list("direction", "text"))
    assert texts[0] == (DemoMessage.Direction.IN, "/id")
    assert "555" in texts[1][1]
    assert response.status_code == 200


def test_foreign_buttons_are_refused(admin_client, demo):
    message = DemoMessage.objects.create(chat_id=1, direction=DemoMessage.Direction.OUT, text="x",
                                         reply_markup={"inline_keyboard": [[{"text": "a", "callback_data": "ok"}]]})

    response = admin_client.post(SIMULATOR, {"action": "press", "chat": 1, "message": message.pk, "data": "forged"})

    assert response.status_code == 404


def test_simulator_needs_permission(demo):
    assert Client().get(SIMULATOR).status_code == 302
    staff = get_user_model().objects.create_user("guard", password="x", is_staff=True)
    client = Client()
    client.force_login(staff)
    assert client.get(SIMULATOR).status_code == 403


def test_simulator_explains_when_learning_mode_is_off(admin_client, settings):
    settings.DEMO_MODE = False

    page = admin_client.get(SIMULATOR).content.decode()

    assert "Учебный режим выключен" in page
