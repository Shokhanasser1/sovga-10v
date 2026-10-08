"""Бюджет подарка. Чистые функции, без БД."""

from decimal import ROUND_FLOOR, Decimal


def gift_budget_uzs(
    price_uzs: int, cost_uzs: int, commission_pct: Decimal, budget_pct: Decimal, cap_uzs: int
) -> int:
    """Доля чистой маржи (после комиссии оплаты или рассрочки), не больше потолка."""
    if min(price_uzs, cost_uzs, cap_uzs) < 0 or commission_pct < 0 or budget_pct < 0:
        raise ValueError("Входные данные не могут быть отрицательными")
    commission = Decimal(price_uzs) * commission_pct / 100
    net_margin = Decimal(price_uzs) - cost_uzs - commission
    if net_margin <= 0:
        return 0
    budget = (net_margin * budget_pct / 100).to_integral_value(rounding=ROUND_FLOOR)
    return int(min(budget, cap_uzs))
