from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.bot.models import DemoMessage
from apps.customers.models import Customer
from apps.notifications.telegram import DEMO_MANAGER_CHAT
from apps.orders.models import Order
from apps.orders.reports import sales_rows
from apps.payments.models import Payment
from apps.sourcing.models import Supplier
from apps.warranty.models import WarrantyCase

pytestmark = pytest.mark.django_db
S = Order.Status


@pytest.fixture
def learning_mode(settings):
    settings.DEMO_MODE = True
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.MANAGER_CHAT_IDS = []


def seed():
    call_command("seed_demo", stdout=None)


def test_history_walks_orders_through_every_stage(learning_mode):
    seed()

    statuses = set(Order.objects.values_list("status", flat=True))
    assert {
        S.SOURCING, S.CONFIRMED, S.PAID, S.PICKING, S.HANDED_TO_CARRIER, S.DELIVERED, S.COMPLETED, S.CANCELLED,
        S.RETURN_REQUESTED, S.INSPECTED, S.REFUNDED,
    } <= statuses
    assert Customer.objects.count() >= 10
    paid = Payment.objects.filter(state__in=[Payment.State.PAID, Payment.State.REFUNDED])
    assert set(paid.values_list("provider", flat=True)) == {Payment.Provider.PAYME, Payment.Provider.CLICK}
    now = timezone.now()
    for order in Order.objects.all():
        assert now - timedelta(days=50) < order.created_at <= now, order.number
        assert order.events.filter(created_at__lte=now).count() == order.events.count()
    assert Order.objects.filter(created_at__lt=now - timedelta(days=30)).exists(), "история за прошлые недели"


def test_history_fills_reports_warranty_and_telegram(learning_mode):
    seed()

    today = timezone.localdate()
    assert len(sales_rows(today - timedelta(days=60), today)) >= 15
    assert WarrantyCase.objects.count() >= 2
    assert DemoMessage.objects.filter(chat_id=DEMO_MANAGER_CHAT).exists()
    customer_chats = Customer.objects.exclude(telegram_chat_id=None).values_list("telegram_chat_id", flat=True)
    assert DemoMessage.objects.filter(chat_id__in=list(customer_chats)).exists()
    supplier_chats = Supplier.objects.exclude(telegram_chat_id=None).values_list("telegram_chat_id", flat=True)
    asks = DemoMessage.objects.filter(chat_id__in=list(supplier_chats), reply_markup__isnull=False)
    assert asks.exists(), "поставщику пришёл запрос с кнопками по заказу, который ждёт ответа"


def test_history_is_created_once(learning_mode):
    seed()
    counts = (Order.objects.count(), Customer.objects.count(), WarrantyCase.objects.count())

    seed()

    assert (Order.objects.count(), Customer.objects.count(), WarrantyCase.objects.count()) == counts


def test_no_history_outside_learning_mode(settings):
    settings.DEMO_MODE = False

    seed()

    assert not Order.objects.exists()
    assert not Customer.objects.exists()


def test_simulator_dates_history_messages_by_their_events(learning_mode):
    started = timezone.now()

    seed()

    messages = DemoMessage.objects.order_by("pk")
    assert messages.filter(created_at__lt=started - timedelta(days=30)).exists(), "старые заказы — старые сообщения"
    times = list(messages.values_list("created_at", flat=True))
    assert times == sorted(times), "переписка в чатах идёт по порядку"
    order = Order.objects.filter(status=S.COMPLETED).order_by("created_at").first()
    first = DemoMessage.objects.filter(chat_id=DEMO_MANAGER_CHAT, text__contains=order.number).order_by("pk").first()
    assert first.created_at == order.created_at, "«Новый заказ» — в минуту оформления"
