from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.inventory.models import InventoryUnit
from apps.orders.desk import sections
from apps.orders.fulfilment import add_unit
from apps.orders.models import Order

from .conftest import NOW
from .test_fulfilment import imei, order, phone_line, units  # noqa: F401 — фикстуры

pytestmark = pytest.mark.django_db
S = Order.Status
DESK = reverse("admin:orders_operatordesk_changelist")


def pick_url(order) -> str:
    return reverse("admin:orders_operatordesk_pick", args=[order.number])


def act(client, order, action, follow=True, **data):
    url = reverse("admin:orders_operatordesk_action", args=[order.number, action])
    return client.post(url, data, follow=follow)


def test_desk_shows_orders_by_stage(admin_client, order):
    page = admin_client.get(DESK).content.decode()

    assert "Рабочее место оператора" in page
    assert order.number in page and "Собираются" in page
    assert 'http-equiv="refresh"' in page


def test_desk_needs_permission(order):
    assert Client().get(DESK).status_code == 302  # на вход в админку
    staff = get_user_model().objects.create_user("guard", password="x", is_staff=True)
    client = Client()
    client.force_login(staff)
    assert client.get(DESK).status_code == 403
    assert client.get(pick_url(order)).status_code == 403
    assert act(client, order, "deliver", follow=False).status_code == 403

    staff.user_permissions.add(Permission.objects.get(codename="change_order"))
    staff = get_user_model().objects.get(pk=staff.pk)
    client.force_login(staff)
    assert client.get(DESK).status_code == 200


def test_actions_need_post_and_csrf(order):
    admin = get_user_model().objects.create_superuser("boss", password="x")
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin)
    url = reverse("admin:orders_operatordesk_action", args=[order.number, "deliver"])

    assert client.get(url).status_code == 405
    assert client.post(url).status_code == 403


def test_scan_and_ship_from_the_pick_page(admin_client, order):
    line = phone_line(order)
    page = act(admin_client, order, "add_unit", line=line.pk, imei=imei(0), uzimei="on").content.decode()
    assert f"IMEI {imei(0)} добавлен" in page
    act(admin_client, order, "add_unit", line=line.pk, imei=imei(1))
    second = InventoryUnit.objects.get(imei1=imei(1))

    page = act(admin_client, order, "ship", carrier="own", courier_name="Азиз", courier_phone="901234567").content.decode()
    assert "нет отметки UzIMEI" in page
    order.refresh_from_db()
    assert order.status == S.PICKING

    act(admin_client, order, "uzimei", unit=second.pk, registered="yes")
    act(admin_client, order, "ship", carrier="own", courier_name="Азиз", courier_phone="901234567")
    order.refresh_from_db()
    assert order.status == S.HANDED_TO_CARRIER

    act(admin_client, order, "deliver")
    order.refresh_from_db()
    assert order.status == S.DELIVERED


def test_errors_are_shown_not_raised(admin_client, order):
    page = act(admin_client, order, "add_unit", line=phone_line(order).pk, imei="123").content.decode()

    assert "Неверный IMEI" in page


def test_remove_unit(admin_client, order):
    unit = add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")

    act(admin_client, order, "remove_unit", unit=unit.pk)

    unit.refresh_from_db()
    assert unit.order_line is None


def test_foreign_lines_and_units_are_not_found(admin_client, order, shop):
    from apps.customers.services import customer_for_phone
    from apps.orders.quote import CartItem
    from apps.orders.services import DeliveryAddress, create_order

    other = create_order(customer_for_phone("+998935554433"), [CartItem("IP16P-256-B", 1)], "card",
                         DeliveryAddress("Ташкент"), "", NOW)

    assert act(admin_client, order, "add_unit", follow=False, line=other.lines.get().pk, imei=imei(0)).status_code == 404
    assert act(admin_client, order, "add_unit", follow=False, line="abc", imei=imei(0)).status_code == 404
    assert act(admin_client, order, "teleport", follow=False).status_code == 404


def test_pick_page(admin_client, order):
    page = admin_client.get(pick_url(order)).content.decode()

    assert "Ташкент" in page and order.customer.phone in page
    assert "нужно ещё 2 IMEI" in page
    assert 'name="imei"' in page and "autofocus" in page
    assert "Собирается <span" in page  # история: название статуса, а не пусто


def test_start_picking_from_the_desk(admin_client, shop, units):
    from apps.customers.services import customer_for_phone
    from apps.orders.quote import CartItem
    from apps.orders.services import DeliveryAddress, create_order

    from .test_fulfilment import paid

    fresh = paid(create_order(customer_for_phone("+998935554433"), [CartItem("IP16P-256-B", 1)], "card",
                              DeliveryAddress("Ташкент"), "", NOW))

    response = act(admin_client, fresh, "start")

    fresh.refresh_from_db()
    assert fresh.status == S.PICKING
    assert response.redirect_chain[-1][0] == pick_url(fresh)


def test_timers(order):
    now = timezone.now()
    picking = next(section for section in sections(now) if section["key"] == "picking")
    assert picking["rows"][0]["timer_class"] in {"ok", "soon"}

    late = next(section for section in sections(now + timedelta(hours=5)) if section["key"] == "picking")
    assert late["rows"][0]["timer"].startswith("просрочен на")
    assert late["rows"][0]["timer_class"] == "late"
