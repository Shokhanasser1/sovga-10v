"""Таблица сравнения с подсветкой лучших значений."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Variant


@dataclass(frozen=True)
class CompareSpec:
    code: str
    name: str
    unit: str
    comparison: str  # higher_better | lower_better | none


@dataclass(frozen=True)
class ComparisonRow:
    code: str
    name: str
    unit: str
    values: tuple
    best: tuple[int, ...]


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def best_indexes(values: Sequence, direction: str) -> list[int]:
    """Индексы лучших значений; пусто, если победителя нет."""
    if direction not in ("higher_better", "lower_better"):
        return []
    numeric = [(index, value) for index, value in enumerate(values) if _is_number(value)]
    if len(numeric) < 2:
        return []
    pick = max if direction == "higher_better" else min
    target = pick(value for _, value in numeric)
    winners = [index for index, value in numeric if value == target]
    return [] if len(winners) == len(numeric) else winners


def build_comparison(specs: Sequence[CompareSpec], items: Sequence[Mapping]) -> list[ComparisonRow]:
    rows = []
    for spec in specs:
        values = tuple(item.get(spec.code) for item in items)
        if all(value is None for value in values):
            continue
        best = tuple(best_indexes(values, spec.comparison))
        rows.append(ComparisonRow(spec.code, spec.name, spec.unit, values, best))
    return rows


def compare_variants(variants: Sequence[Variant], language: str = "ru") -> list[ComparisonRow]:
    if language not in ("ru", "uz"):
        raise ValueError("Язык: ru или uz")
    if not variants:
        return []
    if len({variant.product_model.category_id for variant in variants}) != 1:
        raise ValueError("Сравнивать можно только товары одной категории")
    category = variants[0].product_model.category
    specs = [
        CompareSpec(d.code, getattr(d, f"name_{language}"), d.unit, d.comparison)
        for d in category.effective_attributes()
    ]
    items = [
        {**variant.product_model.attributes, **variant.axes, **variant.attributes}
        for variant in variants
    ]
    return build_comparison(specs, items)
