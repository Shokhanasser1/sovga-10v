"""Оплата при получении: заказ сразу идёт на сборку, деньги берёт курьер."""

from datetime import timedelta

import pytest
from django.urls import reverse

from apps.customers.services import customer_for_phone
from apps.delivery.carriers import Handover
from apps.notifications.models import OutboxEvent
from apps.orders import desk
from apps.orders.fulfilment import add_unit, deliver, ship, start_picking
from apps.orders.models import Order
from apps.orders.quote import CartItem
from apps.orders.returns import open_return
from apps.orders.services import DeliveryAddress, OrderError, cancel_order, confirm_sourcing, create_order
from apps.sourcing.models import Offer, Reservation, Supplier

from .conftest import NOW, stock
from .test_api import BASE, ORDER, browser, post
from .test_fulfilment import imei, units  # noqa: F401 — фикстура

pytestmark = pytest.mark.django_db
S = Order.Status
PHONE_SKU = "IP16P-256-B"


@pytest.fixture
def customer():
    return customer_for_phone("+998901234567")


@pytest.fixture
def cod_on(settings):
    settings.COD_ENABLED = True


def cod_order(customer, now=NOW) -> Order:
    return create_order(customer, [CartItem(PHONE_SKU, 1, gift_sku="CASE-1")], "cod", DeliveryAddress("Ташкент"), "", now)


def test_cod_order_from_own_stock_goes_straight_to_picking_queue(shop, customer, cod_on):
    order = cod_order(customer)

    order.refresh_from_db()
    assert order.status == S.COD
    assert list(order.events.values_list("status_to", flat=True)) == [S.CONFIRMED, S.COD]
    held = {reservation.expires_at for reservation in Reservation.objects.filter(ref=order.number)}
    assert held == {NOW + timedelta(days=7)}, "товар держим, пока заказ собирают и везут"
    event = OutboxEvent.objects.get(type="order.cod")
    assert event.payload == {"number": order.number, "total": order.total_uzs}


def test_cod_order_waits_for_supplier_first(shop, customer, cod_on):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    stock(shop["phone"], 5, supplier=Supplier.objects.create(name="Опт", connector_type=Supplier.Connector.TELEGRAM))
    order = create_order(customer, [CartItem(PHONE_SKU, 1)], "cod", DeliveryAddress("Ташкент"), "", NOW)
    assert order.status == S.SOURCING

    confirmed = confirm_sourcing(order, NOW + timedelta(minutes=20), actor="manager:anna")

    assert confirmed.status == S.COD
    assert Reservation.objects.get(ref=order.number).expires_at == NOW + timedelta(minutes=20, days=7)


def test_customer_cancels_cod_order_until_picking_starts(shop, customer, cod_on, units):  # noqa: F811
    order = cod_order(customer)
    assert cancel_order(order, NOW, actor="customer:x", by_customer=True).status == S.CANCELLED

    second = cod_order(customer)
    start_picking(second, NOW, actor="operator:anna")
    with pytest.raises(OrderError):
        cancel_order(second, NOW, actor="customer:x", by_customer=True)


def test_delivery_records_the_cash_collected(shop, customer, cod_on, units):  # noqa: F811
    order = cod_order(customer)
    start_picking(order, NOW, actor="operator:anna")
    add_unit(order.lines.get(is_gift=False), imei(0), NOW, actor="operator:anna", uzimei_registered=True)
    ship(order, "own", Handover(courier_name="Улугбек", courier_phone="+998935550101"), NOW, actor="operator:anna")

    delivered = deliver(order, NOW, actor="courier")

    total = f"{order.total_uzs:,}".replace(",", " ")
    assert delivered.events.last().note == f"Доставлен, оплата при получении: {total} сум"


def test_api_takes_cod_orders_when_the_shop_accepts_them(shop, customer, cod_on):
    client = browser(customer.user)

    quote = post(client, f"{BASE}/quote/", {"items": ORDER["items"], "payment_method": "cod"}).json()
    response = post(client, f"{BASE}/", {**ORDER, "payment_method": "cod"})

    assert quote["payment_methods"] == ["card", "cod"] and quote["can_order"]
    body = response.json()
    assert response.status_code == 201
    assert (body["status"], body["payment_method"], body["can_pay"], body["can_cancel"]) == ("cod", "cod", False, True)


def test_api_refuses_cod_when_the_shop_does_not_accept_it(shop, customer, settings):
    settings.COD_ENABLED = False
    client = browser(customer.user)

    quote = post(client, f"{BASE}/quote/", {"items": ORDER["items"], "payment_method": "card"}).json()
    response = post(client, f"{BASE}/", {**ORDER, "payment_method": "cod"})

    assert quote["payment_methods"] == ["card"]
    assert response.status_code == 400
    assert "при получении" in str(response.json())
    assert not Order.objects.exists()


def test_operator_sees_how_much_the_courier_collects(shop, customer, cod_on, admin_client, units):  # noqa: F811
    order = cod_order(customer)
    total = f"{order.total_uzs:,}".replace(",", " ")

    to_pick = next(section for section in desk.sections(NOW) if section["key"] == "to_pick")
    [row] = to_pick["rows"]
    assert to_pick["title"] == "К сборке"
    assert f"При получении: взять {total} сум" in row["notes"]
    page = admin_client.get(reverse("admin:orders_operatordesk_pick", args=[order.number])).content.decode()
    assert f"При получении: взять {total} сум" in page


def test_cod_refund_is_paid_back_by_hand(shop, customer, cod_on, units):  # noqa: F811
    order = cod_order(customer)
    start_picking(order, NOW, actor="operator:anna")
    add_unit(order.lines.get(is_gift=False), imei(0), NOW, actor="operator:anna", uzimei_registered=True)
    ship(order, "own", Handover(courier_name="Улугбек", courier_phone="+998935550101"), NOW, actor="operator:anna")
    deliver(order, NOW, actor="courier")
    open_return(order, "Не подошёл", NOW, actor="customer:x")

    message, _ = desk.perform(order, "return_inspect", {"imeis": imei(0), "gift_returned": "on"}, NOW, "operator:anna")

    assert "наличными или переводом" in message and "Payme" not in message


def test_courier_cash_is_not_offered_to_card_orders(shop, customer, cod_on):
    order = create_order(customer, [CartItem(PHONE_SKU, 1)], "card", DeliveryAddress("Ташкент"), "", NOW)

    assert order.status == S.CONFIRMED
    assert not OutboxEvent.objects.filter(type="order.cod").exists()
