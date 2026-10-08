from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from apps.promo.budget import gift_budget_uzs


def test_budget_is_share_of_net_margin():
    # маржа 1 280 000, 10 % = 128 000 < потолка 150 000
    assert gift_budget_uzs(14_080_000, 12_800_000, Decimal("0"), Decimal("10"), 150_000) == 128_000


def test_installment_commission_shrinks_budget():
    # комиссия 5 % = 704 000 → маржа 576 000 → 57 600
    assert gift_budget_uzs(14_080_000, 12_800_000, Decimal("5"), Decimal("10"), 150_000) == 57_600


def test_cap_limits_budget():
    assert gift_budget_uzs(14_080_000, 12_800_000, Decimal("0"), Decimal("50"), 150_000) == 150_000


def test_no_margin_no_gift():
    assert gift_budget_uzs(10_000_000, 10_500_000, Decimal("0"), Decimal("10"), 150_000) == 0


def test_negative_input_rejected():
    with pytest.raises(ValueError):
        gift_budget_uzs(-1, 0, Decimal("0"), Decimal("10"), 150_000)


prices = st.integers(min_value=0, max_value=100_000_000)
percents = st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), places=2)
caps = st.integers(min_value=0, max_value=1_000_000)


@given(price=prices, cost=prices, commission=percents, share=percents, cap=caps)
def test_budget_bounds(price, cost, commission, share, cap):
    budget = gift_budget_uzs(price, cost, commission, share, cap)
    net_margin = Decimal(price) - cost - Decimal(price) * commission / 100

    assert 0 <= budget <= cap
    assert budget <= max(net_margin, 0) * share / 100


@given(price=prices, cost=prices, low=percents, extra=percents, share=percents, cap=caps)
def test_higher_commission_never_increases_budget(price, cost, low, extra, share, cap):
    cheap = gift_budget_uzs(price, cost, low, share, cap)
    expensive = gift_budget_uzs(price, cost, low + extra, share, cap)

    assert expensive <= cheap
