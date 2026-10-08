"""Очередь сопоставления: подсказки SKU для строк прайса и подтверждение привязки."""

import re
from collections.abc import Mapping
from difflib import SequenceMatcher

from django.db import transaction

from apps.catalog.models import Status, Variant

from .importer import upsert_offer
from .models import Offer, SupplierFeedRow, SupplierSkuMap

UNIT_ALIASES = {"гб": "gb", "тб": "tb"}


def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(
        r"(\d+)\s*(gb|гб|tb|тб)\b",
        lambda match: match.group(1) + UNIT_ALIASES.get(match.group(2), match.group(2)),
        text,
    )
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def similarity(a: str, b: str) -> float:
    """0..1, порядок слов не важен."""
    left = " ".join(sorted(normalize(a).split()))
    right = " ".join(sorted(normalize(b).split()))
    return SequenceMatcher(None, left, right).ratio()


def variant_label(variant: Variant, units: Mapping[str, str] | None = None) -> str:
    if units is None:
        units = {d.code: d.unit for d in variant.product_model.category.effective_attributes()}
    parts = [variant.product_model.name_ru]
    parts += [f"{value}{units.get(code, '')}" for code, value in variant.axes.items()]
    return " ".join(parts)


def suggest_variants(
    name: str, limit: int = 5, min_score: float = 0.5
) -> list[tuple[Variant, float]]:
    units_by_category: dict[int, dict[str, str]] = {}
    scored = []
    variants = Variant.objects.exclude(status=Status.ARCHIVED).select_related(
        "product_model__category"
    )
    for variant in variants:
        category = variant.product_model.category
        if category.pk not in units_by_category:
            units_by_category[category.pk] = {
                d.code: d.unit for d in category.effective_attributes()
            }
        score = similarity(name, variant_label(variant, units_by_category[category.pk]))
        if score >= min_score:
            scored.append((variant, score))
    scored.sort(key=lambda item: (-item[1], item[0].sku))
    return scored[:limit]


@transaction.atomic
def confirm_match(row: SupplierFeedRow, variant: Variant) -> Offer | None:
    """Запомнить код поставщика; для корректной строки сразу создать предложение."""
    supplier = row.run.supplier
    SupplierSkuMap.objects.update_or_create(
        supplier=supplier, supplier_code=row.supplier_code, defaults={"variant": variant}
    )
    row.variant = variant
    if row.status == SupplierFeedRow.Status.INVALID:
        row.save(update_fields=["variant"])
        return None
    row.status = SupplierFeedRow.Status.MATCHED
    row.save(update_fields=["variant", "status"])
    return upsert_offer(supplier, variant.pk, row.price_usd, row.qty, row.run.started_at)
