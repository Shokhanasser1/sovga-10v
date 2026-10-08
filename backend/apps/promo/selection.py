"""Публичный сервис: какое правило подарка действует для варианта."""

from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Variant

from .models import GiftPolicy


def select_gift_policy(
    variant: Variant, price_uzs: int, at: datetime | None = None
) -> GiftPolicy | None:
    at = at or timezone.now()
    product = variant.product_model
    category_ids = [category.pk for category in product.category.lineage()]
    return (
        GiftPolicy.objects.filter(is_active=True)
        .filter(Q(category__isnull=True) | Q(category_id__in=category_ids))
        .filter(Q(brand__isnull=True) | Q(brand_id=product.brand_id))
        .filter(Q(min_price_uzs__isnull=True) | Q(min_price_uzs__lte=price_uzs))
        .filter(Q(max_price_uzs__isnull=True) | Q(max_price_uzs__gte=price_uzs))
        .filter(Q(active_from__isnull=True) | Q(active_from__lte=at))
        .filter(Q(active_to__isnull=True) | Q(active_to__gt=at))
        .order_by("-priority", "-pk")
        .first()
    )
