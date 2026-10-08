from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.sourcing.models import Offer, Supplier

pytestmark = pytest.mark.django_db


def make_offer(variant, confirmed_at, **source):
    return Offer.objects.create(
        variant=variant, cost_usd=Decimal("900"), qty_available=3, last_confirmed_at=confirmed_at, **source
    )


def test_offer_needs_exactly_one_source(variant, make_supplier, warehouse):
    now = timezone.now()
    no_source = Offer(variant=variant, cost_usd=Decimal("900"), last_confirmed_at=now)
    both = Offer(variant=variant, cost_usd=Decimal("900"), last_confirmed_at=now,
                 supplier=make_supplier(), warehouse=warehouse)

    for offer in (no_source, both):
        with pytest.raises(ValidationError):
            offer.full_clean()


@pytest.mark.parametrize("connector, hours", [("api", 1), ("sheet", 24), ("file", 24), ("telegram", 6)])
def test_default_ttl_depends_on_connector(make_supplier, connector, hours):
    assert make_supplier(connector_type=connector).effective_ttl == timedelta(hours=hours)


def test_supplier_offer_goes_stale_after_ttl(variant, make_supplier):
    now = timezone.now()
    supplier = make_supplier(connector_type=Supplier.Connector.API)

    fresh = make_offer(variant, now - timedelta(minutes=30), supplier=supplier)
    assert fresh.is_fresh(now)
    assert not fresh.is_fresh(now + timedelta(hours=1))


def test_custom_ttl_overrides_default(variant, make_supplier):
    now = timezone.now()
    offer = make_offer(variant, now - timedelta(hours=3), supplier=make_supplier(ttl_hours=2))

    assert not offer.is_fresh(now)


def test_own_stock_is_always_fresh(variant, warehouse):
    now = timezone.now()
    offer = make_offer(variant, now - timedelta(days=30), warehouse=warehouse)

    assert offer.is_own
    assert offer.is_fresh(now)
