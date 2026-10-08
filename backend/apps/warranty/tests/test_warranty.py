from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.inventory.models import InventoryUnit
from apps.orders.fulfilment import ship
from apps.orders.serializers import order_payload
from apps.orders.services import OrderError
from apps.orders.tests.conftest import NOW, shop  # noqa: F401 — фикстура магазина
from apps.orders.tests.test_fulfilment import imei, order, phone_line, units  # noqa: F401 — фикстуры
from apps.orders.tests.test_shipping import COURIER, picked
from apps.warranty.models import WarrantyCase
from apps.warranty.services import add_months, find_sold_unit, open_case, warranty_info

pytestmark = pytest.mark.django_db
LOOKUP = reverse("admin:warranty_warrantycase_add")


@pytest.fixture
def sold(order):
    ship(picked(order), "own", COURIER, NOW, actor="manager:anna")
    return InventoryUnit.objects.get(imei1=imei(0))


def test_add_months_keeps_the_end_of_month():
    assert add_months(datetime(2026, 1, 31, tzinfo=dt_timezone.utc), 1) == datetime(2026, 2, 28, tzinfo=dt_timezone.utc)
    assert add_months(datetime(2026, 10, 8, tzinfo=dt_timezone.utc), 12) == datetime(2027, 10, 8, tzinfo=dt_timezone.utc)


def test_info_by_imei(sold, order):
    info = warranty_info(find_sold_unit(f" {imei(0)} "))

    assert info.order == order and info.customer_phone == "+998901234567"
    assert info.sold_at == NOW and info.until == add_months(NOW, 12)
    assert info.source == "Ташкент, основной"  # свой склад
    assert info.title == "iPhone 16 Pro · 256 · Чёрный"
    assert info.is_active(NOW + timedelta(days=300))
    assert not info.is_active(NOW + timedelta(days=400))


def test_imei2_and_unknown(sold):
    sold.imei2 = imei(9)
    sold.save()

    assert find_sold_unit(imei(9)) == sold
    assert find_sold_unit(imei(2)) is None  # на складе, не продано
    assert find_sold_unit("nonsense") is None


def test_category_sets_the_term(sold, phones):
    phones.warranty_months = 24
    phones.save()

    assert warranty_info(sold).until == add_months(NOW, 24)


def test_open_case(sold):
    case = open_case(sold, "Не заряжается", "Apple Service Ташкент", NOW + timedelta(days=30), actor="manager:anna")

    assert (case.unit, case.status, case.opened_by) == (sold, WarrantyCase.Status.OPEN, "manager:anna")


def test_case_needs_a_complaint_and_active_warranty(sold):
    with pytest.raises(OrderError, match="неисправност"):
        open_case(sold, " ", "", NOW, actor="manager:anna")
    with pytest.raises(OrderError, match="Гарантия закончилась"):
        open_case(sold, "Не включается", "", NOW + timedelta(days=400), actor="manager:anna")


def test_lookup_page(admin_client, sold, order):
    page = admin_client.get(LOOKUP, {"imei": imei(0)}).content.decode()
    assert order.number in page and "Гарантия до" in page

    response = admin_client.post(LOOKUP, {"imei": imei(0), "complaint": "Не заряжается", "service_center": "Сервис"})

    case = WarrantyCase.objects.get()
    assert response.status_code == 302 and str(case.pk) in response["Location"]
    assert "не найдено" in admin_client.get(LOOKUP, {"imei": imei(2)}).content.decode()


def test_closing_a_case_records_the_time(admin_client, sold):
    case = open_case(sold, "Не заряжается", "", NOW, actor="manager:anna")

    admin_client.post(reverse("admin:warranty_warrantycase_change", args=[case.pk]),
                      {"status": "closed", "service_center": "Сервис", "note": "Заменили аккумулятор"})

    case.refresh_from_db()
    assert case.status == WarrantyCase.Status.CLOSED and case.closed_at is not None


def test_lookup_needs_permission(sold):
    staff = get_user_model().objects.create_user("guard", password="x", is_staff=True)
    client = Client()
    client.force_login(staff)

    assert client.get(LOOKUP, {"imei": imei(0)}).status_code == 403


def test_order_page_shows_devices_and_warranty(sold, order):
    line = next(item for item in order_payload(order)["lines"] if not item["is_gift"])

    until = timezone.localdate(add_months(NOW, 12)).isoformat()  # дата по Ташкенту
    assert line["devices"] == [{"imei": imei(0), "warranty_until": until}, {"imei": imei(1), "warranty_until": until}]
    assert next(item for item in order_payload(order)["lines"] if item["is_gift"])["devices"] == []
