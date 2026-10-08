from decimal import ROUND_CEILING, Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductModel, Status, Variant
from apps.promo.budget import gift_budget_uzs
from apps.promo.selection import select_gift_policy
from apps.sourcing.routing import availability

from .models import PriceSnapshot
from .repricing import current_price


def _gift_budget(variant: Variant, snapshot: PriceSnapshot | None, now) -> int:
    if snapshot is None:
        return 0
    policy = select_gift_policy(variant, snapshot.price_uzs, at=now)
    if policy is None:
        return 0
    cost_uzs = int((snapshot.cost_usd * snapshot.rate).to_integral_value(rounding=ROUND_CEILING))
    return gift_budget_uzs(
        snapshot.price_uzs, cost_uzs, settings.CARD_COMMISSION_PCT,
        policy.budget_pct_of_net_margin, policy.budget_cap_uzs,
    )


class ProductOffersView(APIView):
    """Цена, наличие и бюджет подарка по вариантам — лёгкий запрос для карточки товара.

    Себестоимость и источники наружу не отдаются.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug: str):
        product = get_object_or_404(ProductModel, slug=slug, status=Status.ACTIVE)
        now = timezone.now()
        items = []
        for variant in product.variants.filter(status=Status.ACTIVE).order_by("sku"):
            snapshot = current_price(variant)
            stock = availability(variant, now)
            items.append(
                {
                    "sku": variant.sku,
                    "price_uzs": snapshot.price_uzs if snapshot else None,
                    "availability": {
                        "status": stock.status,
                        "lead_time_days": stock.lead_time_days,
                    },
                    "gift_budget_uzs": _gift_budget(variant, snapshot, now),
                }
            )
        return Response(items)
