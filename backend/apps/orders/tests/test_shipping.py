import pytest

from apps.delivery.carriers import Handover
from apps.delivery.models import Shipment
from apps.inventory.models import InventoryUnit
from apps.orders.fulfilment import add_unit, deliver, ship
from apps.orders.models import Order
from apps.orders.serializers import order_payload
from apps.orders.services import OrderError, cancel_order
from apps.sourcing.models import Offer, Reservation

from .conftest import NOW
from .test_fulfilment import imei, order, phone_line, supplier_order, units  # noqa: F401 — фикстуры

pytestmark = pytest.mark.django_db
S = Order.Status
U = InventoryUnit.State
COURIER = Handover(courier_name="Азиз", courier_phone="90 123 45 67")


def picked(order) -> Order:
    for n in range(phone_line(order).qty):
        add_unit(phone_line(order), imei(n), NOW, actor="manager:anna", uzimei_registered=True)
    return order


def test_no_shipping_without_imei_and_uzimei(order):
    add_unit(phone_line(order), imei(0), NOW, actor="manager:anna")

    with pytest.raises(OrderError) as error:
        ship(order, "own", COURIER, NOW, actor="manager:anna")

    assert "нужно ещё 1 IMEI" in error.value.message and "нет отметки UzIMEI" in error.value.message
    order.refresh_from_db()
    assert order.status == S.PICKING and not Shipment.objects.exists()


@pytest.mark.parametrize(
    "carrier, handover",
    [
        ("own", Handover(courier_name="Азиз")),
        ("own", Handover(courier_name="Азиз", courier_phone="12345")),
        ("service", Handover(service_name="BTS")),
        ("pigeon", COURIER),
    ],
)
def test_handover_details_are_required(order, carrier, handover):
    with pytest.raises(OrderError):
        ship(picked(order), carrier, handover, NOW, actor="manager:anna")

    order.refresh_from_db()
    assert order.status == S.PICKING


def test_shipping_sells_devices_and_writes_off_stock(order, shop):
    gift_offer = Offer.objects.get(variant=shop["case"])

    shipped = ship(picked(order), "own", COURIER, NOW, actor="manager:anna")

    assert shipped.status == S.HANDED_TO_CARRIER
    shipment = Shipment.objects.get(order=order)
    assert (shipment.courier_name, shipment.courier_phone, shipment.handed_at) == ("Азиз", "+998901234567", NOW)
    assert set(InventoryUnit.objects.filter(order_line__order=order).values_list("status", flat=True)) == {U.SOLD}
    assert not Reservation.objects.filter(ref=order.number, released_at__isnull=True).exists()
    assert Offer.objects.get(variant=shop["phone"], warehouse=shop["warehouse"]).qty_available == 1
    gift_offer_after = Offer.objects.get(pk=gift_offer.pk)
    assert gift_offer_after.qty_available == gift_offer.qty_available - 2
    assert order.events.last().note == "Курьер Азиз, +998901234567"


def test_supplier_stock_is_written_off(supplier_order):
    offer = phone_line(supplier_order).offer
    add_unit(phone_line(supplier_order), imei(10), NOW, actor="manager:anna", uzimei_registered=True)

    ship(supplier_order, "service", Handover(service_name="BTS", tracking="BTS-778899"), NOW, actor="manager:anna")

    assert Offer.objects.get(pk=offer.pk).qty_available == offer.qty_available - 1
    assert InventoryUnit.objects.get(imei1=imei(10)).status == U.SOLD


def test_delivery(order):
    with pytest.raises(OrderError):
        deliver(order, NOW, actor="manager:anna")
    ship(picked(order), "own", COURIER, NOW, actor="manager:anna")

    delivered = deliver(order, NOW, actor="manager:anna")

    assert delivered.status == S.DELIVERED
    assert Shipment.objects.get(order=order).delivered_at == NOW


def test_cancel_while_picking_returns_own_devices(order):
    picked(order)

    cancel_order(order, NOW, actor="manager:anna")

    assert set(InventoryUnit.objects.values_list("status", flat=True)) == {U.IN_STOCK}
    assert not InventoryUnit.objects.filter(order_line__isnull=False).exists()


def test_cancel_while_picking_forgets_supplier_devices(supplier_order):
    add_unit(phone_line(supplier_order), imei(10), NOW, actor="manager:anna")

    cancel_order(supplier_order, NOW, actor="manager:anna")

    assert not InventoryUnit.objects.filter(imei1=imei(10)).exists()


def test_order_page_shows_the_courier(order):
    assert order_payload(order)["shipment"] is None

    ship(picked(order), "own", COURIER, NOW, actor="manager:anna")

    assert order_payload(order)["shipment"] == {
        "carrier": "own", "courier_name": "Азиз", "courier_phone": "+998901234567", "service_name": "", "tracking": "",
    }
