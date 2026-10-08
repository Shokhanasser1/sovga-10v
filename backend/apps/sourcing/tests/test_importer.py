from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.sourcing.feeds import FeedRow
from apps.sourcing.importer import import_feed
from apps.sourcing.models import Offer, SupplierFeedRow, SupplierSkuMap

pytestmark = pytest.mark.django_db


def row(code, price="999.00", qty=5, error=""):
    return FeedRow(code, f"товар {code}", Decimal(price), qty, {"code": code}, error)


@pytest.fixture
def supplier(make_supplier, variant):
    supplier = make_supplier(lead_time_days=2)
    SupplierSkuMap.objects.create(supplier=supplier, supplier_code="IP16P-256-BLK", variant=variant)
    return supplier


def test_matched_row_creates_offer(supplier, variant):
    now = timezone.now()

    run = import_feed(supplier, [row("IP16P-256-BLK", price="1010.50", qty=4)], now)

    offer = Offer.objects.get(variant=variant, supplier=supplier)
    assert (offer.cost_usd, offer.qty_available, offer.lead_time_days) == (Decimal("1010.50"), 4, 2)
    assert offer.last_confirmed_at == now
    assert run.rows.get().status == SupplierFeedRow.Status.MATCHED


def test_next_import_updates_same_offer(supplier, variant):
    now = timezone.now()
    import_feed(supplier, [row("IP16P-256-BLK", price="1010.50")], now)

    import_feed(supplier, [row("IP16P-256-BLK", price="990.00", qty=1)], now + timedelta(hours=1))

    offer = Offer.objects.get(variant=variant, supplier=supplier)
    assert (offer.cost_usd, offer.qty_available) == (Decimal("990.00"), 1)


def test_unknown_code_goes_to_matching_queue(supplier):
    run = import_feed(supplier, [row("NEW-CODE")], timezone.now())

    queued = run.rows.get()
    assert queued.status == SupplierFeedRow.Status.UNMATCHED
    assert queued.variant is None
    assert queued.name == "товар NEW-CODE"


def test_invalid_row_is_kept_with_error(supplier):
    run = import_feed(supplier, [row("IP16P-256-BLK", error="некорректная цена")], timezone.now())

    stored = run.rows.get()
    assert stored.status == SupplierFeedRow.Status.INVALID
    assert stored.error == "некорректная цена"
    assert not Offer.objects.exists()


def test_item_missing_from_price_list_is_sold_out(supplier, variant):
    now = timezone.now()
    import_feed(supplier, [row("IP16P-256-BLK", qty=4)], now)

    import_feed(supplier, [row("OTHER")], now + timedelta(hours=1))

    offer = Offer.objects.get(variant=variant, supplier=supplier)
    assert offer.qty_available == 0
    assert offer.last_confirmed_at == now + timedelta(hours=1)


def test_run_counts(supplier):
    run = import_feed(
        supplier,
        [row("IP16P-256-BLK"), row("NEW-1"), row("NEW-2"), row("BAD", error="нет кода")],
        timezone.now(),
    )

    assert (run.rows_total, run.rows_matched, run.rows_unmatched, run.rows_invalid) == (4, 1, 2, 1)
