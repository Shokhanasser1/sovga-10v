import pytest
from django.urls import reverse
from django.utils import timezone

from apps.customers.services import customer_for_phone
from apps.notifications.models import OutboxEvent
from apps.orders.models import Order
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, create_order
from apps.sourcing.models import Offer, Supplier

from .conftest import stock

pytestmark = pytest.mark.django_db

CHANGELIST = reverse("admin:orders_order_changelist")


@pytest.fixture
def sourcing_order(shop):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    stock(shop["phone"], 5, supplier=Supplier.objects.create(name="TG", connector_type="telegram"))
    customer = customer_for_phone("+998901234567")
    return create_order(customer, [CartItem("IP16P-256-B", 1)], "card", DeliveryAddress("Ташкент"), "", timezone.now())


def run_action(admin_client, action, order):
    return admin_client.post(CHANGELIST, {"action": action, "_selected_action": [order.pk]}, follow=True)


def test_manager_confirms_supplier_availability(admin_client, admin_user, sourcing_order):
    run_action(admin_client, "confirm_sourcing_action", sourcing_order)

    sourcing_order.refresh_from_db()
    assert sourcing_order.status == Order.Status.CONFIRMED
    assert sourcing_order.events.last().actor == f"manager:{admin_user.username}"


def test_manager_cancels_order(admin_client, sourcing_order):
    run_action(admin_client, "cancel_action", sourcing_order)

    sourcing_order.refresh_from_db()
    assert sourcing_order.status == Order.Status.CANCELLED


def test_wrong_action_shows_a_warning_and_changes_nothing(admin_client, sourcing_order):
    run_action(admin_client, "confirm_sourcing_action", sourcing_order)

    page = run_action(admin_client, "confirm_sourcing_action", sourcing_order).content.decode()

    assert "Заказ уже не ждёт подтверждения поставщика" in page


def test_order_page_shows_lines_and_history(admin_client, sourcing_order):
    page = admin_client.get(reverse("admin:orders_order_change", args=[sourcing_order.pk])).content.decode()

    assert "IP16P-256-B" in page
    assert "Заказ оформлен" in page


def test_failed_events_can_be_retried(admin_client):
    event = OutboxEvent.objects.create(
        type="order.created", payload={}, status=OutboxEvent.Status.FAILED, attempts=7, next_attempt_at=timezone.now()
    )

    admin_client.post(
        reverse("admin:notifications_outboxevent_changelist"),
        {"action": "retry", "_selected_action": [event.pk]},
    )

    event.refresh_from_db()
    assert (event.status, event.attempts) == (OutboxEvent.Status.PENDING, 0)


def test_view_only_staff_cannot_run_actions(client, sourcing_order):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission

    viewer = get_user_model().objects.create_user(username="viewer", password="x", is_staff=True)
    viewer.user_permissions.add(
        Permission.objects.get(codename="view_order"), Permission.objects.get(codename="view_outboxevent")
    )
    client.force_login(viewer)
    event = OutboxEvent.objects.create(
        type="order.created", payload={}, status=OutboxEvent.Status.FAILED, attempts=7, next_attempt_at=timezone.now()
    )

    client.post(CHANGELIST, {"action": "cancel_action", "_selected_action": [sourcing_order.pk]})
    client.post(
        reverse("admin:notifications_outboxevent_changelist"), {"action": "retry", "_selected_action": [event.pk]}
    )

    sourcing_order.refresh_from_db()
    event.refresh_from_db()
    assert sourcing_order.status == Order.Status.SOURCING
    assert event.status == OutboxEvent.Status.FAILED
