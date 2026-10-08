from decimal import Decimal

import pytest

from apps.customers.services import customer_for_phone
from apps.inventory.imei import with_check_digit
from apps.inventory.models import InventoryUnit
from apps.inventory.services import receive_unit
from apps.orders.fulfilment import add_unit, mark_uzimei, picking_problems, remove_unit, start_picking
from apps.orders.models import Order
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, OrderError, cancel_order, create_order
from apps.payments.services import confirm_payment, start_payment
from apps.sourcing.models import Offer, Supplier

from .conftest import NOW, stock

pytestmark = pytest.mark.django_db
S = Order.Status
U = InventoryUnit.State
Z = InventoryUnit.UzimeiStatus


def imei(n: int) -> str:
    return with_check_digit(f"3569380356{n:04d}")


@pytest.fixture
def units(shop):
    return [
        receive_unit(variant=shop["phone"], warehouse=shop["warehouse"], cost_usd=Decimal("1000"), imei1=imei(n))
        for n in range(3)
    ]


def paid(order: Order) -> Order:
    start_payment(order, NOW, actor="payme")
    return confirm_payment(order, NOW, actor="payme", provider="Payme")


@pytest.fixture
def order(shop, units):
    customer = customer_for_phone("+998901234567")
    order = create_order(
        customer, [CartItem("IP16P-256-B", 2, gift_sku="CASE-1")], "card", DeliveryAddress("Ташкент"), "", NOW
    )
    paid(order)
    return start_picking(order, NOW, actor="manager:anna")


def phone_line(order):
    return order.lines.get(is_gift=False)


def test_only_paid_orders_are_picked(shop, units):
    order = create_order(customer_for_phone("+998901234567"), [CartItem("IP16P-256-B", 1)], "card",
                         DeliveryAddress("Ташкент"), "", NOW)

    with pytest.raises(OrderError):
        start_picking(order, NOW, actor="manager:anna")

    picking = start_picking(paid(order), NOW, actor="manager:anna")
    assert picking.status == S.PICKING


def test_scan_binds_a_unit_from_stock(order, units):
    unit = add_unit(phone_line(order), imei(0), NOW, actor="manager:anna", uzimei_registered=True)

    unit.refresh_from_db()
    assert unit.pk == units[0].pk
    assert (unit.status, unit.order_line, unit.uzimei_status) == (U.RESERVED, phone_line(order), Z.REGISTERED)


@pytest.mark.parametrize("value", ["123", "35693803560000" + "9", "٣٥٦٩٣٨٠٣٥٦٠٠٠٠٨", ""])
def test_wrong_imei(order, value):
    with pytest.raises(OrderError, match="IMEI"):
        add_unit(phone_line(order), value, NOW, actor="manager:anna")


def test_typo_does_not_create_a_device_for_own_stock(order):
    with pytest.raises(OrderError, match="нет"):
        add_unit(phone_line(order), imei(77), NOW, actor="manager:anna")

    assert InventoryUnit.objects.count() == 3


def test_unit_of_another_model(order, shop, make_variant, iphone):
    white = make_variant(iphone, "IP16P-256-W", {"storage_gb": 256, "color": "white"})
    white.save()
    receive_unit(variant=white, warehouse=shop["warehouse"], cost_usd=Decimal("1000"), imei1=imei(50))

    with pytest.raises(OrderError, match="другой модификации"):
        add_unit(phone_line(order), imei(50), NOW, actor="manager:anna")


def test_unit_cannot_go_into_two_orders(order, units):
    add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")

    with pytest.raises(OrderError, match="уже"):
        add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")


def test_no_extra_units(order):
    add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")
    add_unit(phone_line(order), imei(1), NOW, actor="manager:anna")

    with pytest.raises(OrderError, match="все устройства"):
        add_unit(phone_line(order), imei(2), NOW, actor="manager:anna")


def test_gift_needs_no_device(order):
    with pytest.raises(OrderError, match="без IMEI"):
        add_unit(order.lines.get(is_gift=True), imei(0), NOW, actor="manager:anna")


def test_only_while_picking(order):
    cancel_order(order, NOW, actor="manager:anna")

    with pytest.raises(OrderError, match="не собирается"):
        add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")


@pytest.fixture
def supplier_order(shop):
    Offer.objects.filter(variant=shop["phone"], warehouse__isnull=False).delete()
    stock(shop["phone"], 5, supplier=Supplier.objects.create(name="Опт", connector_type=Supplier.Connector.API))
    order = create_order(customer_for_phone("+998901234567"), [CartItem("IP16P-256-B", 1)], "card",
                         DeliveryAddress("Ташкент"), "", NOW)
    return start_picking(paid(order), NOW, actor="manager:anna")


def test_supplier_device_is_received_on_scan(supplier_order, shop):
    unit = add_unit(phone_line(supplier_order), imei(10), NOW, actor="manager:anna")

    assert (unit.variant, unit.warehouse, unit.status) == (shop["phone"], shop["warehouse"], U.RESERVED)
    assert unit.cost_usd == phone_line(supplier_order).cost_usd


def test_supplier_device_imei_must_be_new(supplier_order, units):
    with pytest.raises(OrderError, match="уже есть"):
        add_unit(phone_line(supplier_order), imei(0), NOW, actor="manager:anna")


def test_removed_own_unit_goes_back_to_stock(order):
    own = add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")

    remove_unit(own, NOW, actor="manager:anna")

    own.refresh_from_db()
    assert (own.status, own.order_line) == (U.IN_STOCK, None)


def test_removed_supplier_unit_is_forgotten(supplier_order):
    foreign = add_unit(phone_line(supplier_order), imei(10), NOW, actor="manager:anna")

    remove_unit(foreign, NOW, actor="manager:anna")

    assert not InventoryUnit.objects.filter(imei1=imei(10)).exists()


def test_picking_problems(order):
    line = phone_line(order)
    assert picking_problems(order) == ["iPhone 16 Pro · 256 · Чёрный: нужно ещё 2 IMEI"]

    first = add_unit(line, imei(0), NOW, actor="manager:anna", uzimei_registered=True)
    second = add_unit(line, imei(1), NOW, actor="manager:anna")
    assert picking_problems(order) == [f"IMEI {imei(1)}: нет отметки UzIMEI"]

    mark_uzimei(second, registered=False, now=NOW, actor="manager:anna")
    assert picking_problems(order) == [f"IMEI {imei(1)}: не зарегистрирован в UzIMEI — замените устройство"]

    mark_uzimei(second, registered=True, now=NOW, actor="manager:anna")
    first.refresh_from_db()
    assert picking_problems(order) == []
