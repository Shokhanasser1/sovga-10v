from datetime import timedelta

import pytest
from django.urls import reverse

from apps.inventory.models import InventoryUnit
from apps.orders.fulfilment import deliver, ship
from apps.orders.models import Order, ReturnRequest
from apps.orders.returns import complete_delivered, inspect_return, open_return, refund_return, reject_return
from apps.orders.services import OrderError

from .conftest import NOW
from .test_fulfilment import imei, order, phone_line, units  # noqa: F401 — фикстуры
from .test_shipping import COURIER, picked

pytestmark = pytest.mark.django_db
S = Order.Status
R = ReturnRequest.Status
U = InventoryUnit.State
GIFT_PRICE = 120_000  # CASE-1 из магазина тестов, по штуке на каждый из 2 телефонов


@pytest.fixture
def delivered(order, settings):
    settings.RETURN_DAYS = 10
    ship(picked(order), "own", COURIER, NOW, actor="manager:anna")
    return deliver(order, NOW, actor="manager:anna")


def requested(order, reason="Не подошёл размер"):
    return open_return(order, reason, NOW + timedelta(days=2), actor="manager:anna")


def test_gift_value_is_remembered(order):
    gift = order.lines.get(is_gift=True)

    assert (gift.price_uzs, gift.gift_value_uzs) == (0, GIFT_PRICE)


def test_return_is_opened_within_the_window(delivered):
    request = requested(delivered)

    delivered.refresh_from_db()
    assert delivered.status == S.RETURN_REQUESTED
    assert (request.status, request.reason) == (R.REQUESTED, "Не подошёл размер")


def test_return_window(delivered):
    with pytest.raises(OrderError, match="Срок возврата"):
        open_return(delivered, "Передумал", NOW + timedelta(days=11), actor="manager:anna")


def test_return_needs_a_delivered_order_and_a_reason(order, delivered):
    with pytest.raises(OrderError, match="причину"):
        open_return(delivered, "  ", NOW, actor="manager:anna")
    requested(delivered)
    with pytest.raises(OrderError, match="доставленный"):
        requested(delivered)


def test_accepted_return_with_gift(delivered):
    requested(delivered)

    request = inspect_return(delivered, [imei(1), imei(0)], gift_returned=True, now=NOW, actor="manager:anna")

    assert (request.status, request.refund_amount_uzs) == (R.ACCEPTED, delivered.total_uzs)
    assert set(InventoryUnit.objects.filter(order_line__order=delivered).values_list("status", flat=True)) == {U.RETURNED}
    delivered.refresh_from_db()
    assert delivered.status == S.INSPECTED


def test_kept_gift_is_withheld(delivered):
    requested(delivered)

    request = inspect_return(delivered, [imei(0), imei(1)], gift_returned=False, now=NOW, actor="manager:anna")

    assert request.refund_amount_uzs == delivered.total_uzs - 2 * GIFT_PRICE
    assert "удержана цена подарка 240 000 сум" in delivered.events.order_by("-pk").first().note


@pytest.mark.parametrize("brought", [[imei(0)], [imei(0), imei(2)], [imei(0), imei(1), imei(2)], []])
def test_foreign_or_missing_device_means_refusal(delivered, brought):
    requested(delivered)

    request = inspect_return(delivered, brought, gift_returned=True, now=NOW, actor="manager:anna")

    assert request.status == R.REJECTED
    delivered.refresh_from_db()
    assert delivered.status == S.COMPLETED
    assert set(InventoryUnit.objects.filter(order_line__order=delivered).values_list("status", flat=True)) == {U.SOLD}


def test_manual_refusal_needs_a_note(delivered):
    requested(delivered)
    with pytest.raises(OrderError, match="причину"):
        reject_return(delivered, "", NOW, actor="manager:anna")

    reject_return(delivered, "Следы падения", NOW, actor="manager:anna")

    delivered.refresh_from_db()
    assert delivered.status == S.COMPLETED
    assert ReturnRequest.objects.get(order=delivered).status == R.REJECTED


def test_refund(delivered):
    requested(delivered)
    inspect_return(delivered, [imei(0), imei(1)], gift_returned=True, now=NOW, actor="manager:anna")

    request = refund_return(delivered, NOW, actor="manager:anna")

    assert (request.status, request.refunded_at) == (R.REFUNDED, NOW)
    delivered.refresh_from_db()
    assert delivered.status == S.REFUNDED
    with pytest.raises(OrderError):
        refund_return(delivered, NOW, actor="manager:anna")


def test_delivered_orders_complete_after_the_window(delivered):
    assert complete_delivered(NOW + timedelta(days=9)) == 0

    assert complete_delivered(NOW + timedelta(days=11)) == 1

    delivered.refresh_from_db()
    assert delivered.status == S.COMPLETED


def test_return_in_progress_is_not_completed(delivered):
    requested(delivered)

    assert complete_delivered(NOW + timedelta(days=30)) == 0


def act(client, order, action, **data):
    return client.post(reverse("admin:orders_operatordesk_action", args=[order.number, action]), data, follow=True)


def test_return_from_the_operator_desk(admin_client, delivered, settings):
    settings.RETURN_DAYS = 10_000  # действия идут с текущим временем
    page = admin_client.get(reverse("admin:orders_operatordesk_pick", args=[delivered.number])).content.decode()
    assert "Оформить возврат" in page

    act(admin_client, delivered, "return_open", reason="Не понравился цвет")
    page = act(admin_client, delivered, "return_inspect", imeis=f"{imei(0)}\r\n{imei(1)}\r\n", gift_returned="on")
    assert "Верните покупателю" in page.content.decode()

    act(admin_client, delivered, "return_refund")
    delivered.refresh_from_db()
    assert delivered.status == S.REFUNDED


def test_desk_search(admin_client, delivered):
    by_number = admin_client.get(reverse("admin:orders_operatordesk_changelist"), {"q": delivered.number.lower()})
    assert by_number.status_code == 302 and delivered.number in by_number["Location"]

    by_phone = admin_client.get(reverse("admin:orders_operatordesk_changelist"), {"q": "90 123 45 67"})
    assert by_phone.status_code == 302

    nothing = admin_client.get(reverse("admin:orders_operatordesk_changelist"), {"q": "SG999999"})
    assert "Ничего не найдено" in nothing.content.decode()
