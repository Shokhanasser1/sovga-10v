from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from apps.pricing.calculator import PriceInputs, needs_reprice, sale_price_uzs


def inputs(**overrides):
    values = dict(
        cost_usd=Decimal("1000"), rate=Decimal("12800"), markup_pct=Decimal("10"),
        min_margin_uzs=300_000, rounding_step_uzs=1000,
    )
    values.update(overrides)
    return PriceInputs(**values)


def test_markup_applied():
    # 1000 × 12 800 = 12 800 000; +10 % = 14 080 000
    assert sale_price_uzs(inputs()) == 14_080_000


def test_rounding_goes_up_to_step():
    # 999.99 × 12 800 × 1.1 = 14 079 859.2 → 14 080 000
    assert sale_price_uzs(inputs(cost_usd=Decimal("999.99"))) == 14_080_000


def test_min_margin_wins_over_small_markup():
    # 1 280 000 × 1.01 = 1 292 800 < 1 280 000 + 300 000
    assert sale_price_uzs(inputs(cost_usd=Decimal("100"), markup_pct=Decimal("1"))) == 1_580_000


@pytest.mark.parametrize(
    "field, value",
    [
        ("cost_usd", Decimal("0")),
        ("rate", Decimal("-1")),
        ("markup_pct", Decimal("-5")),
        ("min_margin_uzs", -1),
        ("rounding_step_uzs", 0),
    ],
)
def test_invalid_inputs_rejected(field, value):
    with pytest.raises(ValueError):
        sale_price_uzs(inputs(**{field: value}))


money = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("20000"), places=2)
rates = st.decimals(min_value=Decimal("1000"), max_value=Decimal("50000"), places=2)
percents = st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), places=2)
margins = st.integers(min_value=0, max_value=5_000_000)
steps = st.sampled_from([1, 100, 1000, 10_000])


@given(cost=money, rate=rates, markup=percents, margin=margins, step=steps)
def test_price_never_below_cost_plus_min_margin(cost, rate, markup, margin, step):
    price = sale_price_uzs(PriceInputs(cost, rate, markup, margin, step))

    assert price >= cost * rate + margin
    assert price % step == 0


@given(cost=money, rate=rates, markup=percents, margin=margins, step=steps)
def test_rounding_adds_less_than_one_step(cost, rate, markup, margin, step):
    price = sale_price_uzs(PriceInputs(cost, rate, markup, margin, step))
    raw = max(cost * rate * (1 + markup / 100), cost * rate + margin)

    assert price - raw < step


@given(cost=money, extra=money, rate=rates, markup=percents, margin=margins, step=steps)
def test_more_expensive_purchase_never_lowers_price(cost, extra, rate, markup, margin, step):
    cheap = sale_price_uzs(PriceInputs(cost, rate, markup, margin, step))
    pricey = sale_price_uzs(PriceInputs(cost + extra, rate, markup, margin, step))

    assert pricey >= cheap


def test_needs_reprice_only_above_threshold():
    assert not needs_reprice(Decimal("12800"), Decimal("12860"))  # +0.47 %
    assert needs_reprice(Decimal("12800"), Decimal("12870"))  # +0.55 %
    assert needs_reprice(Decimal("12800"), Decimal("12730"))  # −0.55 %
