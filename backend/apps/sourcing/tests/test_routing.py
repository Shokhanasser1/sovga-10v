from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.sourcing.models import Offer, Supplier
from apps.sourcing.reservations import release, release_expired, reserve
from apps.sourcing.routing import Availability, availability, choose_offer, offer_score

pytestmark = pytest.mark.django_db

NOW = timezone.now()


@pytest.fixture
def offer(variant):
    def factory(cost="1000", qty=3, lead=1, confirmed_at=NOW, **source):
        return Offer.objects.create(
            variant=variant, cost_usd=Decimal(cost), qty_available=qty, lead_time_days=lead,
            last_confirmed_at=confirmed_at, **source,
        )

    return factory


def test_offer_score():
    assert offer_score(Decimal("1000"), 0, Decimal("1")) == Decimal("1000")
    assert offer_score(Decimal("1000"), 2, Decimal("1")) == Decimal("1020")
    assert offer_score(Decimal("1000"), 0, Decimal("0.8")) == Decimal("1250")


def test_own_stock_wins_even_if_supplier_is_cheaper(variant, offer, warehouse, make_supplier):
    own = offer(cost="1100", lead=0, warehouse=warehouse)
    offer(cost="900", supplier=make_supplier())

    assert choose_offer(variant, 1, NOW) == own


def test_best_supplier_by_score(variant, offer, warehouse, make_supplier):
    offer(cost="800", qty=0, warehouse=warehouse)
    offer(cost="1000", lead=5, supplier=make_supplier("медленный"))  # 1050
    fast = offer(cost="1030", lead=1, supplier=make_supplier("быстрый"))  # 1040.3

    assert choose_offer(variant, 1, NOW) == fast


def test_unreliable_supplier_loses(variant, offer, make_supplier):
    offer(cost="1000", supplier=make_supplier("ненадёжный", reliability=Decimal("0.80")))  # 1262.5
    reliable = offer(cost="1100", supplier=make_supplier("надёжный"))  # 1111

    assert choose_offer(variant, 1, NOW) == reliable


def test_stale_inactive_and_short_offers_are_skipped(variant, offer, make_supplier):
    api = Supplier.Connector.API
    offer(cost="500", confirmed_at=NOW - timedelta(hours=2), supplier=make_supplier("старый", connector_type=api))
    offer(cost="600", supplier=make_supplier("выключен", is_active=False))
    inactive = offer(cost="700", supplier=make_supplier("снято с продажи"))
    inactive.is_active = False
    inactive.save()
    offer(cost="800", qty=1, supplier=make_supplier("мало"))

    assert choose_offer(variant, 2, NOW) is None


@pytest.mark.parametrize(
    "setup, expected",
    [
        ("own", Availability("in_stock", 0)),
        ("fresh_supplier", Availability("in_stock", 2)),
        ("stale_supplier", Availability("on_order", 3)),
        ("nothing", Availability("out_of_stock", None)),
    ],
)
def test_availability(variant, offer, warehouse, make_supplier, setup, expected):
    api = Supplier.Connector.API
    if setup == "own":
        offer(lead=0, warehouse=warehouse)
    elif setup == "fresh_supplier":
        offer(lead=2, supplier=make_supplier())
    elif setup == "stale_supplier":
        offer(lead=2, confirmed_at=NOW - timedelta(hours=2), supplier=make_supplier(connector_type=api))

    assert availability(variant, NOW) == expected


def test_reservation_takes_stock_until_it_expires(variant, offer, warehouse):
    offer(qty=1, lead=0, warehouse=warehouse)

    reservation = reserve(variant, 1, "cart-1", NOW)

    assert reservation is not None and not reservation.is_soft
    assert availability(variant, NOW).status == "out_of_stock"
    assert reserve(variant, 1, "cart-2", NOW) is None
    later = NOW + timedelta(minutes=16)
    assert availability(variant, later).status == "in_stock"
    assert release_expired(later) == 1


def test_released_reservation_frees_stock(variant, offer, warehouse):
    offer(qty=1, warehouse=warehouse)
    reservation = reserve(variant, 1, "cart-1", NOW)

    release(reservation, NOW)

    assert availability(variant, NOW).status == "in_stock"


def test_supplier_reservation_is_soft(variant, offer, make_supplier):
    offer(supplier=make_supplier())

    assert reserve(variant, 2, "cart-1", NOW).is_soft


def test_reserve_requires_positive_qty(variant):
    with pytest.raises(ValueError):
        reserve(variant, 0, "cart-1", NOW)
