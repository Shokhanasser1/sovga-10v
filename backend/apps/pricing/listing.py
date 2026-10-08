"""Кэш листинга: цена «от» и доступность модели товара."""

from datetime import datetime

from apps.catalog.models import ProductModel, Status
from apps.sourcing.routing import OUT_OF_STOCK, availability

from .repricing import current_price


def refresh_listing_cache(now: datetime) -> int:
    """Цена «от» — среди доступных вариантов; если доступных нет — среди всех с ценой."""
    products = list(ProductModel.objects.prefetch_related("variants"))
    for product in products:
        available_prices: list[int] = []
        all_prices: list[int] = []
        is_available = False
        for variant in product.variants.all():
            if variant.status != Status.ACTIVE:
                continue
            snapshot = current_price(variant)
            variant_available = availability(variant, now).status != OUT_OF_STOCK
            is_available = is_available or variant_available
            if snapshot is not None:
                all_prices.append(snapshot.price_uzs)
                if variant_available:
                    available_prices.append(snapshot.price_uzs)
        product.price_from_uzs = min(available_prices or all_prices, default=None)
        product.is_available = is_available
    ProductModel.objects.bulk_update(products, ["price_from_uzs", "is_available"], batch_size=500)
    return len(products)
