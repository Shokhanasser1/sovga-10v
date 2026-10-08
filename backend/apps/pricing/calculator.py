"""Расчёт цены продажи в сумах. Чистые функции, без БД."""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal


@dataclass(frozen=True)
class PriceInputs:
    cost_usd: Decimal
    rate: Decimal  # сумов за 1 USD с учётом спреда
    markup_pct: Decimal
    min_margin_uzs: int
    rounding_step_uzs: int


def sale_price_uzs(inputs: PriceInputs) -> int:
    """max(наценка, минимальная маржа), округление вверх до шага."""
    if inputs.cost_usd <= 0 or inputs.rate <= 0:
        raise ValueError("Закупка и курс должны быть положительными")
    if inputs.markup_pct < 0 or inputs.min_margin_uzs < 0:
        raise ValueError("Наценка и минимальная маржа не могут быть отрицательными")
    if inputs.rounding_step_uzs < 1:
        raise ValueError("Шаг округления — минимум 1 сум")
    cost_uzs = inputs.cost_usd * inputs.rate
    with_markup = cost_uzs * (1 + inputs.markup_pct / 100)
    floor = cost_uzs + inputs.min_margin_uzs
    raw = max(with_markup, floor)
    steps = (raw / inputs.rounding_step_uzs).to_integral_value(rounding=ROUND_CEILING)
    return int(steps) * inputs.rounding_step_uzs


def needs_reprice(
    old_rate: Decimal, new_rate: Decimal, threshold_pct: Decimal = Decimal("0.5")
) -> bool:
    """Пересчитывать цены, только если курс сдвинулся больше порога."""
    if old_rate <= 0:
        return True
    change_pct = abs(new_rate - old_rate) / old_rate * 100
    return change_pct > threshold_pct
