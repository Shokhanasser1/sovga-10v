from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.sourcing.feeds import FeedRow
from apps.sourcing.importer import import_feed
from apps.sourcing.models import Offer, SupplierSkuMap

pytestmark = pytest.mark.django_db


def test_matching_queue_shows_suggestions_and_confirms(admin_client, make_supplier, variant):
    supplier = make_supplier()
    run = import_feed(
        supplier, [FeedRow("X-1", "iPhone 16 Pro 256GB <b>Black</b>", Decimal("1000"), 3, {})], timezone.now()
    )
    row = run.rows.get()
    url = reverse("admin:sourcing_supplierfeedrow_change", args=[row.pk])

    page = admin_client.get(url).content.decode()
    assert variant.sku in page
    assert "<b>Black</b>" not in page  # имя из прайса экранируется

    response = admin_client.post(url, {"variant": variant.pk})

    assert response.status_code == 302
    assert SupplierSkuMap.objects.get(supplier_code="X-1").variant == variant
    assert Offer.objects.get(supplier=supplier).qty_available == 3


def test_adding_unit_in_admin_updates_own_offer(admin_client, variant, warehouse):
    response = admin_client.post(reverse("admin:inventory_inventoryunit_add"), {
        "variant": variant.pk, "warehouse": warehouse.pk, "imei1": "490154203237518", "imei2": "",
        "serial": "", "uzimei_status": "registered", "purchase_batch": "", "cost_usd": "1000",
        "status": "in_stock",
    })

    assert response.status_code == 302
    assert Offer.objects.get(variant=variant, warehouse=warehouse).qty_available == 1
