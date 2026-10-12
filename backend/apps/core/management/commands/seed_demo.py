"""Демо-каталог для разработки и показа витрины. Повторный запуск ничего не дублирует."""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    AccessoryCompat,
    AttributeDefinition,
    Brand,
    Category,
    CompatRule,
    ProductModel,
    Status,
    Variant,
)
from apps.catalog.search import rebuild_search_index
from apps.core import demo_catalog as data
from apps.inventory.imei import with_check_digit
from apps.inventory.models import InventoryUnit
from apps.inventory.services import receive_unit
from apps.pricing.listing import refresh_listing_cache
from apps.pricing.models import ExchangeRate, MarkupRule
from apps.pricing.repricing import reprice_all
from apps.promo.models import GiftPolicy
from apps.sourcing.models import Offer, Supplier, Warehouse


class Command(BaseCommand):
    help = "Заполнить базу демо-каталогом: товары, склад с IMEI, поставщики, курс, наценки, подарки"

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        now = timezone.now()
        categories = self._categories()
        brands = {slug: Brand.objects.update_or_create(slug=slug, defaults={"name": name})[0]
                  for slug, name in data.BRANDS}
        warehouse, _ = Warehouse.objects.get_or_create(name="Ташкент, основной склад")
        suppliers = self._suppliers()
        products = {}
        for slug, category, brand, name_ru, name_uz, attributes, variants in data.PRODUCTS:
            description_ru, description_uz = data.DESCRIPTIONS[slug]
            product, _ = ProductModel.objects.update_or_create(
                slug=slug,
                defaults={"category": categories[category], "brand": brands[brand], "name_ru": name_ru,
                          "name_uz": name_uz, "description_ru": description_ru, "description_uz": description_uz,
                          "attributes": attributes, "status": Status.ACTIVE,
                          "is_accessory": category in data.ACCESSORY_CATEGORIES},
            )
            products[slug] = product
            supplier = suppliers["second" if brand in data.SECOND_SUPPLIER_BRANDS else "main"]
            for sku, axes, cost in variants:
                variant, _ = Variant.objects.update_or_create(
                    sku=sku,
                    defaults={"product_model": product, "axes": axes, "mxik_code": data.DEMO_MXIK,
                              "package_code": "1500", "status": Status.ACTIVE, "giftable": sku in data.GIFTABLE},
                )
                self._stock(variant, Decimal(cost), warehouse, supplier, suppliers["stale"], now)
        self._compatibility(products)
        self._pricing_rules(categories)
        rate = ExchangeRate.objects.order_by("-date").first()
        result = reprice_all(rate, now)
        rebuild_search_index()
        refresh_listing_cache(now)
        self.stdout.write(
            f"Демо-каталог готов: {len(products)} товаров, цен обновлено {result.changed}. "
            f"Курс {rate.cbu_rate} на {rate.date}."
        )

    def _categories(self) -> dict[str, Category]:
        result = {}
        for slug, name_ru, name_uz, serialized, attributes in data.CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug, defaults={"name_ru": name_ru, "name_uz": name_uz, "is_serialized": serialized}
            )
            for order, (code, ru, uz, kind, unit, level, axis, facet, comparison, enum) in enumerate(attributes):
                AttributeDefinition.objects.update_or_create(
                    category=category, code=code,
                    defaults={"name_ru": ru, "name_uz": uz, "type": kind, "unit": unit, "level": level,
                              "is_variant_axis": axis, "is_facet": facet, "comparison": comparison,
                              "enum_values": enum, "sort_order": order * 10},
                )
            result[slug] = category
        return result

    def _suppliers(self) -> dict[str, Supplier]:
        main, _ = Supplier.objects.update_or_create(
            name="Демо-поставщик (Google Sheets)",
            defaults={"connector_type": Supplier.Connector.SHEET, "lead_time_days": 1},
        )
        second, _ = Supplier.objects.update_or_create(
            name="Демо-поставщик Samsung и Honor (Excel)",
            defaults={"connector_type": Supplier.Connector.FILE, "lead_time_days": 2,
                      "reliability": Decimal("0.95")},
        )
        stale, _ = Supplier.objects.update_or_create(
            name="Демо-поставщик (Telegram)",
            defaults={"connector_type": Supplier.Connector.TELEGRAM, "lead_time_days": 2,
                      "reliability": Decimal("0.90")},
        )
        return {"main": main, "second": second, "stale": stale}

    def _stock(self, variant, cost, warehouse, supplier, stale, now) -> None:
        own_units = data.OWN_STOCK.get(variant.sku, 0)
        existing = InventoryUnit.objects.filter(variant=variant).count()
        for number in range(existing, own_units):
            payload = f"35{variant.pk:06d}{number:06d}"[:14]
            receive_unit(variant=variant, warehouse=warehouse, cost_usd=cost,
                         imei1=with_check_digit(payload))
        if not variant.product_model.category.is_serialized:
            Offer.objects.update_or_create(
                variant=variant, warehouse=warehouse,
                defaults={"cost_usd": cost, "qty_available": 25, "last_confirmed_at": now},
            )
            return
        if variant.sku in data.STALE_SUPPLIER_SKUS:
            supplier, confirmed = stale, now - timedelta(days=2)
        else:
            confirmed = now
        Offer.objects.update_or_create(
            variant=variant, supplier=supplier,
            defaults={"cost_usd": cost + 20, "qty_available": 10, "lead_time_days": supplier.lead_time_days,
                      "last_confirmed_at": confirmed},
        )

    def _compatibility(self, products) -> None:
        for device, _, _ in data.CASES:
            AccessoryCompat.objects.get_or_create(accessory=products[data.case_slug(device)], device=products[device])
        for device, *_ in data.GLASSES:
            AccessoryCompat.objects.get_or_create(accessory=products[data.glass_slug(device)], device=products[device])
        for slug in data.POWER_ACCESSORIES:
            CompatRule.objects.get_or_create(
                accessory=products[slug],
                defaults={"conditions": [
                    {"attr": "charge_port", "op": "eq", "value": "usb-c"},
                    {"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"},
                ]},
            )

    def _pricing_rules(self, categories) -> None:
        if not ExchangeRate.objects.exists():
            ExchangeRate.objects.create(date=timezone.localdate(), cbu_rate=Decimal("11800"))
        MarkupRule.objects.update_or_create(
            variant=None, category=None, brand=None, is_active=True,
            defaults={"markup_pct": Decimal("12"), "min_margin_uzs": 300_000, "rounding_step_uzs": 10_000},
        )
        # Аксессуары недорогие, чтобы чехлы и стёкла помещались в бюджет подарка к смартфону (до 150 000 сум).
        for slug, (pct, min_margin, step) in data.MARKUPS.items():
            MarkupRule.objects.update_or_create(
                category=categories[slug], is_active=True,
                defaults={"markup_pct": pct, "min_margin_uzs": min_margin, "rounding_step_uzs": step},
            )
        GiftPolicy.objects.get_or_create(
            name="Смартфоны: подарок до 150 000 сум", category=categories["smartphones"],
            defaults={"budget_pct_of_net_margin": Decimal("15"), "budget_cap_uzs": 150_000},
        )
