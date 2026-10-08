from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import Brand, ProductModel, Status
from apps.sourcing.feeds import FeedRow
from apps.sourcing.importer import import_feed
from apps.sourcing.matching import confirm_match, normalize, similarity, suggest_variants
from apps.sourcing.models import Offer, SupplierFeedRow, SupplierSkuMap


def test_normalize_unifies_case_units_and_punctuation():
    assert normalize("iPhone 16 Pro, 256 ГБ — Чёрный") == "iphone 16 pro 256gb черный"
    assert normalize("256GB") == normalize("256 gb")


def test_similarity_ignores_word_order():
    assert similarity("Black iPhone 16 Pro 256GB", "iPhone 16 Pro 256 GB black") == 1.0


@pytest.mark.django_db
def test_suggestions_rank_best_variant_first(variant, iphone, phones, make_variant):
    make_variant(iphone, "IP16P-512-W", {"storage_gb": 512, "color": "white"}).save()
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(category=phones, brand=samsung, slug="galaxy-s26",
                                         name_ru="Galaxy S26", name_uz="Galaxy S26")
    make_variant(galaxy, "S26-256-B", {"storage_gb": 256, "color": "black"}).save()

    suggestions = suggest_variants("Apple iPhone 16 Pro 256GB Black")

    skus = [v.sku for v, _ in suggestions]
    scores = [score for _, score in suggestions]
    assert skus[0] == variant.sku
    assert skus.index("IP16P-512-W") > 0
    assert scores == sorted(scores, reverse=True)


@pytest.mark.django_db
def test_unrelated_names_get_no_suggestions(variant):
    assert suggest_variants("Наушники Sony WH-1000XM5") == []


@pytest.mark.django_db
def test_archived_variants_are_not_suggested(variant):
    variant.status = Status.ARCHIVED
    variant.save()

    assert suggest_variants("iPhone 16 Pro 256 black") == []


@pytest.mark.django_db
def test_confirm_match_maps_code_and_creates_offer(make_supplier, variant):
    supplier = make_supplier()
    started = timezone.now() - timedelta(minutes=5)
    run = import_feed(supplier, [FeedRow("X-1", "iPhone", Decimal("1000"), 3, {})], started)
    row = run.rows.get()

    offer = confirm_match(row, variant)

    row.refresh_from_db()
    assert row.status == SupplierFeedRow.Status.MATCHED
    assert SupplierSkuMap.objects.get(supplier=supplier, supplier_code="X-1").variant == variant
    assert (offer.cost_usd, offer.qty_available, offer.last_confirmed_at) == (Decimal("1000.00"), 3, started)

    next_run = import_feed(supplier, [FeedRow("X-1", "iPhone", Decimal("990"), 2, {})], timezone.now())
    assert next_run.rows_matched == 1
    assert Offer.objects.get(supplier=supplier).cost_usd == Decimal("990.00")


@pytest.mark.django_db
def test_confirm_match_on_invalid_row_maps_code_only(make_supplier, variant):
    supplier = make_supplier()
    run = import_feed(supplier, [FeedRow("X-1", "iPhone", None, 3, {}, "некорректная цена")], timezone.now())

    assert confirm_match(run.rows.get(), variant) is None
    assert SupplierSkuMap.objects.filter(supplier_code="X-1").exists()
    assert not Offer.objects.exists()
