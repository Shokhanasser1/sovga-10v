import pytest
from django.utils import timezone

from apps.catalog.models import Status
from apps.orders.quote import CartItem, quote

pytestmark = pytest.mark.django_db

NOW = timezone.now()
PHONE = "IP16P-256-B"


def test_totals_and_gift_options(shop):
    result = quote([CartItem(PHONE, 2)], "card", NOW)

    [line] = result.lines
    assert (line.unit_price_uzs, line.line_total_uzs, result.total_uzs) == (14_080_000, 28_160_000, 28_160_000)
    assert line.availability == "in_stock"
    # маржа 14 080 000 − 12 800 000 = 1 280 000; 10 % = 128 000 ≤ потолка 150 000
    assert line.gift_budget_uzs == 128_000
    assert [option.sku for option in line.gift_options] == ["CASE-1"]
    assert result.can_order


def test_installment_commission_shrinks_the_gift(shop, settings):
    settings.INSTALLMENT_COMMISSION_PCT = 5

    [line] = quote([CartItem(PHONE, 1)], "installment", NOW).lines

    assert line.gift_budget_uzs == 57_600
    assert line.gift_options == []


def test_valid_gift_choice(shop):
    [line] = quote([CartItem(PHONE, 1, gift_sku="CASE-1")], "card", NOW).lines

    assert line.gift.sku == "CASE-1"
    assert line.errors == []


@pytest.mark.parametrize("gift", ["CASE-PREMIUM", "CASE-REMOTE", "CASE-PLAIN", "CASE-OTHER", "NOPE"])
def test_invalid_gift_choice(shop, gift):
    result = quote([CartItem(PHONE, 1, gift_sku=gift)], "card", NOW)

    assert result.lines[0].errors == ["Этот подарок недоступен — выберите другой"]
    assert not result.can_order


def test_unknown_and_unpublished_products(shop):
    shop["phone"].status = Status.DRAFT
    shop["phone"].save()

    result = quote([CartItem(PHONE, 1), CartItem("NOPE", 1)], "card", NOW)

    assert [line.errors for line in result.lines] == [["Товар больше не продаётся"]] * 2
    assert result.total_uzs == 0


def test_not_enough_stock(shop):
    result = quote([CartItem(PHONE, 4)], "card", NOW)

    assert result.lines[0].errors == ["Столько нет в наличии — уменьшите количество"]


def test_without_price(shop):
    shop["phone"].price_snapshots.all().delete()

    assert quote([CartItem(PHONE, 1)], "card", NOW).lines[0].errors == ["Цена уточняется — оформить пока нельзя"]


def test_cart_limits(shop):
    many = [CartItem(f"SKU-{n}", 1) for n in range(11)]

    assert quote(many, "card", NOW).errors == ["В корзине не больше 10 позиций"]
    assert quote([CartItem(PHONE, 1), CartItem(PHONE, 1)], "card", NOW).errors == ["Товар повторяется в корзине"]
    assert quote([], "card", NOW).errors == ["Корзина пуста"]
