"""Загрузка прайса поставщика в базу: предложения + очередь сопоставления."""

from collections import Counter
from datetime import datetime
from decimal import Decimal

from django.db import transaction

from .feeds import FeedRow
from .models import Offer, Supplier, SupplierFeedRow, SupplierFeedRun


def upsert_offer(
    supplier: Supplier, variant_id: int, price_usd: Decimal, qty: int, confirmed_at: datetime
) -> Offer:
    offer, _ = Offer.objects.update_or_create(
        variant_id=variant_id,
        supplier=supplier,
        defaults={
            "cost_usd": price_usd,
            "qty_available": qty,
            "lead_time_days": supplier.lead_time_days,
            "last_confirmed_at": confirmed_at,
            "is_active": True,
        },
    )
    return offer


@transaction.atomic
def import_feed(supplier: Supplier, rows: list[FeedRow], now: datetime) -> SupplierFeedRun:
    """Прайс — полный снимок: чего в нём нет, того у поставщика нет."""
    run = SupplierFeedRun.objects.create(supplier=supplier, started_at=now)
    mapping = dict(supplier.sku_maps.values_list("supplier_code", "variant_id"))
    seen_variant_ids: set[int] = set()
    counts: Counter[str] = Counter()
    Status = SupplierFeedRow.Status
    for row in rows:
        variant_id = None
        if row.error:
            status = Status.INVALID
        elif row.code in mapping:
            status = Status.MATCHED
            variant_id = mapping[row.code]
            upsert_offer(supplier, variant_id, row.price_usd, row.qty, now)
            seen_variant_ids.add(variant_id)
        else:
            status = Status.UNMATCHED
        SupplierFeedRow.objects.create(
            run=run, supplier_code=row.code, name=row.name[:300], price_usd=row.price_usd,
            qty=row.qty, raw=row.raw, status=status, error=row.error, variant_id=variant_id,
        )
        counts[status] += 1
    supplier.offers.exclude(variant_id__in=seen_variant_ids).update(
        qty_available=0, last_confirmed_at=now
    )
    run.rows_total = len(rows)
    run.rows_matched = counts[Status.MATCHED]
    run.rows_unmatched = counts[Status.UNMATCHED]
    run.rows_invalid = counts[Status.INVALID]
    run.save()
    return run
