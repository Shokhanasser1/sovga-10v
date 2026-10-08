"""Расчёт корзины: цены, наличие, бюджет подарка и варианты подарка.

Один и тот же расчёт показывает покупателю корзину и проверяет заказ при оформлении.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.conf import settings

from apps.catalog.compatibility import compatible_accessories
from apps.catalog.models import Status, Variant
from apps.pricing.repricing import current_price, snapshot_cost_uzs
from apps.promo.budget import gift_budget_uzs
from apps.promo.selection import select_gift_policy
from apps.sourcing.routing import availability, choose_offer

MAX_LINES = 10
MAX_QTY = 5


@dataclass(frozen=True)
class CartItem:
    sku: str
    qty: int
    gift_sku: str | None = None


@dataclass(frozen=True)
class GiftOption:
    sku: str
    name_ru: str
    name_uz: str
    price_uzs: int


@dataclass
class QuoteLine:
    sku: str
    qty: int
    variant: Variant | None = None
    unit_price_uzs: int | None = None
    line_total_uzs: int = 0
    availability: str = "out_of_stock"
    gift_budget_uzs: int = 0
    gift_options: list[GiftOption] = field(default_factory=list)
    gift: GiftOption | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class Quote:
    lines: list[QuoteLine]
    total_uzs: int
    errors: list[str]

    @property
    def can_order(self) -> bool:
        return bool(self.lines) and not self.errors and all(not line.errors for line in self.lines)


def commission_pct(payment_method: str) -> Decimal:
    value = settings.INSTALLMENT_COMMISSION_PCT if payment_method == "installment" else settings.CARD_COMMISSION_PCT
    return Decimal(str(value))


def _cart_errors(items: list[CartItem]) -> list[str]:
    if not items:
        return ["Корзина пуста"]
    if len(items) > MAX_LINES:
        return ["В корзине не больше 10 позиций"]
    if len({item.sku for item in items}) != len(items):
        return ["Товар повторяется в корзине"]
    return []


def sellable_variant(sku: str) -> Variant | None:
    return (
        Variant.objects.select_related("product_model__category", "product_model__brand")
        .filter(sku=sku, status=Status.ACTIVE, product_model__status=Status.ACTIVE)
        .first()
    )


def gift_options(variant: Variant, budget: int, qty: int, now: datetime) -> list[GiftOption]:
    """Совместимые подарочные аксессуары со своего склада, не дороже бюджета; дорогие — первыми."""
    if budget <= 0:
        return []
    candidates = Variant.objects.filter(
        product_model__in=compatible_accessories(variant.product_model), giftable=True, status=Status.ACTIVE
    ).select_related("product_model")
    options = []
    for gift in candidates:
        snapshot = current_price(gift)
        if snapshot is None or snapshot.price_uzs > budget:
            continue
        offer = choose_offer(gift, qty, now)
        if offer is None or not offer.is_own:
            continue
        product = gift.product_model
        options.append(GiftOption(gift.sku, product.name_ru, product.name_uz, snapshot.price_uzs))
    return sorted(options, key=lambda option: (-option.price_uzs, option.sku))


def _quote_line(item: CartItem, payment_method: str, now: datetime) -> QuoteLine:
    line = QuoteLine(sku=item.sku, qty=item.qty)
    if not 1 <= item.qty <= MAX_QTY:
        line.errors.append("Количество — от 1 до 5")
        return line
    variant = sellable_variant(item.sku)
    if variant is None:
        line.errors.append("Товар больше не продаётся")
        return line
    line.variant = variant
    line.availability = availability(variant, now).status
    snapshot = current_price(variant)
    if snapshot is None:
        line.errors.append("Цена уточняется — оформить пока нельзя")
        return line
    line.unit_price_uzs = snapshot.price_uzs
    line.line_total_uzs = snapshot.price_uzs * item.qty
    if choose_offer(variant, item.qty, now) is None:
        line.errors.append("Столько нет в наличии — уменьшите количество")
    policy = select_gift_policy(variant, snapshot.price_uzs, at=now)
    if policy:
        line.gift_budget_uzs = gift_budget_uzs(
            snapshot.price_uzs, snapshot_cost_uzs(snapshot), commission_pct(payment_method),
            policy.budget_pct_of_net_margin, policy.budget_cap_uzs,
        )
    line.gift_options = gift_options(variant, line.gift_budget_uzs, item.qty, now)
    if item.gift_sku:
        line.gift = next((option for option in line.gift_options if option.sku == item.gift_sku), None)
        if line.gift is None:
            line.errors.append("Этот подарок недоступен — выберите другой")
    return line


def quote(items: list[CartItem], payment_method: str, now: datetime) -> Quote:
    errors = _cart_errors(items)
    if errors:
        return Quote([], 0, errors)
    lines = [_quote_line(item, payment_method, now) for item in items]
    return Quote(lines, sum(line.line_total_uzs for line in lines), [])
