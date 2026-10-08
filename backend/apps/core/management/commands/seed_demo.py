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
from apps.inventory.imei import with_check_digit
from apps.inventory.models import InventoryUnit
from apps.inventory.services import receive_unit
from apps.pricing.listing import refresh_listing_cache
from apps.pricing.models import ExchangeRate, MarkupRule
from apps.pricing.repricing import reprice_all
from apps.promo.models import GiftPolicy
from apps.sourcing.models import Offer, Supplier, Warehouse

T = AttributeDefinition.Type
L = AttributeDefinition.Level
C = AttributeDefinition.Comparison
DEMO_MXIK = "08517001001000000"

PHONE_ATTRIBUTES = [
    # code, ru, uz, type, unit, level, axis, facet, comparison, enum
    ("storage_gb", "Память", "Xotira", T.NUMBER, "ГБ", L.VARIANT, True, True, C.HIGHER_BETTER, []),
    ("color", "Цвет", "Rang", T.ENUM, "", L.VARIANT, True, True, C.NONE,
     ["black", "white", "blue", "green", "titanium", "grey"]),
    ("sim", "SIM", "SIM", T.ENUM, "", L.VARIANT, True, True, C.NONE, ["nano_esim", "esim_only", "dual_sim"]),
    ("ram_gb", "Оперативная память", "Operativ xotira", T.NUMBER, "ГБ", L.MODEL, False, True, C.HIGHER_BETTER, []),
    ("screen_in", "Экран", "Ekran", T.NUMBER, "″", L.MODEL, False, False, C.NONE, []),
    ("chipset", "Процессор", "Protsessor", T.TEXT, "", L.MODEL, False, False, C.NONE, []),
    ("battery_mah", "Аккумулятор", "Batareya", T.NUMBER, "мА·ч", L.MODEL, False, False, C.HIGHER_BETTER, []),
    ("max_charge_w", "Быстрая зарядка", "Tez quvvatlash", T.NUMBER, "Вт", L.MODEL, False, False,
     C.HIGHER_BETTER, []),
    ("charge_port", "Разъём", "Ulagich", T.ENUM, "", L.MODEL, False, True, C.NONE, ["usb-c", "lightning"]),
    ("nfc", "NFC", "NFC", T.BOOL, "", L.MODEL, False, True, C.NONE, []),
    ("weight_g", "Вес", "Og'irlik", T.NUMBER, "г", L.MODEL, False, False, C.LOWER_BETTER, []),
]
TABLET_ATTRIBUTES = [row for row in PHONE_ATTRIBUTES if row[0] in (
    "storage_gb", "color", "ram_gb", "screen_in", "chipset", "battery_mah", "weight_g"
)]
ACCESSORY_ATTRIBUTES = [
    ("color", "Цвет", "Rang", T.ENUM, "", L.VARIANT, True, True, C.NONE, ["black", "white", "clear"]),
    ("output_w", "Мощность", "Quvvat", T.NUMBER, "Вт", L.MODEL, False, True, C.HIGHER_BETTER, []),
    ("connector", "Разъём", "Ulagich", T.ENUM, "", L.MODEL, False, True, C.NONE, ["usb-c", "lightning"]),
]

CATEGORIES = [
    # slug, ru, uz, serialized, attributes
    ("smartphones", "Смартфоны", "Smartfonlar", True, PHONE_ATTRIBUTES),
    ("tablets", "Планшеты", "Planshetlar", True, TABLET_ATTRIBUTES),
    ("cases", "Чехлы", "G'iloflar", False, ACCESSORY_ATTRIBUTES[:1]),
    ("chargers", "Зарядные устройства", "Quvvatlagichlar", False, ACCESSORY_ATTRIBUTES[1:]),
    ("headphones", "Наушники", "Quloqchinlar", False, []),
]

BRANDS = [("apple", "Apple"), ("samsung", "Samsung"), ("xiaomi", "Xiaomi"), ("anker", "Anker"),
          ("spigen", "Spigen")]

# slug, category, brand, ru, uz, attributes, variants: (sku, axes, cost_usd)
PRODUCTS = [
    ("iphone-16-pro", "smartphones", "apple", "iPhone 16 Pro", "iPhone 16 Pro",
     {"ram_gb": 8, "screen_in": 6.3, "chipset": "A18 Pro", "battery_mah": 3582, "max_charge_w": 30,
      "charge_port": "usb-c", "nfc": True, "weight_g": 199},
     [("IP16P-128-BLK", {"storage_gb": 128, "color": "black", "sim": "nano_esim"}, "950"),
      ("IP16P-256-BLK", {"storage_gb": 256, "color": "black", "sim": "nano_esim"}, "1050"),
      ("IP16P-256-TIT", {"storage_gb": 256, "color": "titanium", "sim": "nano_esim"}, "1060"),
      ("IP16P-512-TIT", {"storage_gb": 512, "color": "titanium", "sim": "nano_esim"}, "1250"),
      # Американская версия: Apple продаёт её только с eSIM — на карточке будет предупреждение
      ("IP16P-256-US", {"storage_gb": 256, "color": "black", "sim": "esim_only"}, "990")]),
    ("iphone-15", "smartphones", "apple", "iPhone 15", "iPhone 15",
     {"ram_gb": 6, "screen_in": 6.1, "chipset": "A16 Bionic", "battery_mah": 3349, "max_charge_w": 20,
      "charge_port": "usb-c", "nfc": True, "weight_g": 171},
     [("IP15-128-BLK", {"storage_gb": 128, "color": "black", "sim": "nano_esim"}, "650"),
      ("IP15-128-BLU", {"storage_gb": 128, "color": "blue", "sim": "nano_esim"}, "650"),
      ("IP15-256-BLK", {"storage_gb": 256, "color": "black", "sim": "nano_esim"}, "750")]),
    ("galaxy-s25-ultra", "smartphones", "samsung", "Galaxy S25 Ultra", "Galaxy S25 Ultra",
     {"ram_gb": 12, "screen_in": 6.9, "chipset": "Snapdragon 8 Elite", "battery_mah": 5000,
      "max_charge_w": 45, "charge_port": "usb-c", "nfc": True, "weight_g": 218},
     [("S25U-256-BLK", {"storage_gb": 256, "color": "black", "sim": "dual_sim"}, "1000"),
      ("S25U-512-TIT", {"storage_gb": 512, "color": "titanium", "sim": "dual_sim"}, "1150")]),
    ("galaxy-a56", "smartphones", "samsung", "Galaxy A56", "Galaxy A56",
     {"ram_gb": 8, "screen_in": 6.7, "chipset": "Exynos 1580", "battery_mah": 5000, "max_charge_w": 45,
      "charge_port": "usb-c", "nfc": True, "weight_g": 198},
     [("A56-128-BLK", {"storage_gb": 128, "color": "black", "sim": "dual_sim"}, "330"),
      ("A56-256-GRN", {"storage_gb": 256, "color": "green", "sim": "dual_sim"}, "380")]),
    ("redmi-note-14-pro", "smartphones", "xiaomi", "Redmi Note 14 Pro", "Redmi Note 14 Pro",
     {"ram_gb": 8, "screen_in": 6.67, "chipset": "Dimensity 7300", "battery_mah": 5110, "max_charge_w": 45,
      "charge_port": "usb-c", "nfc": True, "weight_g": 190},
     [("RN14P-256-BLK", {"storage_gb": 256, "color": "black", "sim": "dual_sim"}, "260"),
      ("RN14P-256-BLU", {"storage_gb": 256, "color": "blue", "sim": "dual_sim"}, "260")]),
    ("ipad-air-11", "tablets", "apple", "iPad Air 11", "iPad Air 11",
     {"ram_gb": 8, "screen_in": 11, "chipset": "M2", "battery_mah": 7606, "weight_g": 462},
     [("IPAD-AIR-128-BLU", {"storage_gb": 128, "color": "blue"}, "600"),
      ("IPAD-AIR-256-GRY", {"storage_gb": 256, "color": "grey"}, "700")]),
    ("case-iphone-16-pro", "cases", "spigen", "Чехол Spigen для iPhone 16 Pro",
     "iPhone 16 Pro uchun Spigen g'ilofi", {},
     [("CASE-IP16P-BLK", {"color": "black"}, "9"), ("CASE-IP16P-CLR", {"color": "clear"}, "8")]),
    ("case-galaxy-s25-ultra", "cases", "spigen", "Чехол Spigen для Galaxy S25 Ultra",
     "Galaxy S25 Ultra uchun Spigen g'ilofi", {},
     [("CASE-S25U-BLK", {"color": "black"}, "9")]),
    ("charger-anker-30w", "chargers", "anker", "Зарядное устройство Anker 30 Вт USB-C",
     "Anker 30 Vt USB-C quvvatlagichi", {"output_w": 30, "connector": "usb-c"},
     [("CHG-ANKER-30", {}, "12")]),
    ("charger-samsung-45w", "chargers", "samsung", "Зарядное устройство Samsung 45 Вт",
     "Samsung 45 Vt quvvatlagichi", {"output_w": 45, "connector": "usb-c"},
     [("CHG-SAMSUNG-45", {}, "25")]),
    ("airpods-pro-2", "headphones", "apple", "AirPods Pro 2", "AirPods Pro 2", {},
     [("AIRPODS-PRO-2", {}, "190")]),
]

OWN_STOCK = {"IP16P-256-BLK": 3, "IP16P-128-BLK": 2, "IP15-128-BLK": 2}
STALE_SUPPLIER_SKUS = {"RN14P-256-BLU", "S25U-512-TIT"}
GIFTABLE = {"CASE-IP16P-BLK", "CASE-IP16P-CLR", "CASE-S25U-BLK", "CHG-ANKER-30"}


class Command(BaseCommand):
    help = "Заполнить базу демо-каталогом: товары, склад с IMEI, поставщики, курс, наценки, подарки"

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        now = timezone.now()
        categories = self._categories()
        brands = {slug: Brand.objects.update_or_create(slug=slug, defaults={"name": name})[0]
                  for slug, name in BRANDS}
        warehouse, _ = Warehouse.objects.get_or_create(name="Ташкент, основной склад")
        fresh, _ = Supplier.objects.update_or_create(
            name="Демо-поставщик (Google Sheets)",
            defaults={"connector_type": Supplier.Connector.SHEET, "lead_time_days": 1},
        )
        stale, _ = Supplier.objects.update_or_create(
            name="Демо-поставщик (Telegram)",
            defaults={"connector_type": Supplier.Connector.TELEGRAM, "lead_time_days": 2,
                      "reliability": Decimal("0.90")},
        )
        products = {}
        for slug, category, brand, name_ru, name_uz, attributes, variants in PRODUCTS:
            product, _ = ProductModel.objects.update_or_create(
                slug=slug,
                defaults={"category": categories[category], "brand": brands[brand], "name_ru": name_ru,
                          "name_uz": name_uz, "attributes": attributes, "status": Status.ACTIVE,
                          "is_accessory": category in ("cases", "chargers", "headphones")},
            )
            products[slug] = product
            for sku, axes, cost in variants:
                variant, _ = Variant.objects.update_or_create(
                    sku=sku,
                    defaults={"product_model": product, "axes": axes, "mxik_code": DEMO_MXIK,
                              "package_code": "1500", "status": Status.ACTIVE, "giftable": sku in GIFTABLE},
                )
                self._stock(variant, Decimal(cost), warehouse, fresh, stale, now)
        self._compatibility(products)
        self._pricing_rules(categories, now)
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
        for slug, name_ru, name_uz, serialized, attributes in CATEGORIES:
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

    def _stock(self, variant, cost, warehouse, fresh, stale, now) -> None:
        own_units = OWN_STOCK.get(variant.sku, 0)
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
        if variant.sku in STALE_SUPPLIER_SKUS:
            supplier, confirmed = stale, now - timedelta(days=2)
        else:
            supplier, confirmed = fresh, now
        Offer.objects.update_or_create(
            variant=variant, supplier=supplier,
            defaults={"cost_usd": cost + 20, "qty_available": 10, "lead_time_days": supplier.lead_time_days,
                      "last_confirmed_at": confirmed},
        )

    def _compatibility(self, products) -> None:
        AccessoryCompat.objects.get_or_create(accessory=products["case-iphone-16-pro"],
                                              device=products["iphone-16-pro"])
        AccessoryCompat.objects.get_or_create(accessory=products["case-galaxy-s25-ultra"],
                                              device=products["galaxy-s25-ultra"])
        for slug in ("charger-anker-30w", "charger-samsung-45w"):
            CompatRule.objects.get_or_create(
                accessory=products[slug],
                defaults={"conditions": [
                    {"attr": "charge_port", "op": "eq", "value": "usb-c"},
                    {"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"},
                ]},
            )

    def _pricing_rules(self, categories, now) -> None:
        if not ExchangeRate.objects.exists():
            ExchangeRate.objects.create(date=timezone.localdate(), cbu_rate=Decimal("11800"))
        MarkupRule.objects.update_or_create(
            variant=None, category=None, brand=None, is_active=True,
            defaults={"markup_pct": Decimal("12"), "min_margin_uzs": 300_000, "rounding_step_uzs": 10_000},
        )
        # Аксессуары недорогие, чтобы чехлы помещались в бюджет подарка к смартфону (до 150 000 сум).
        for slug in ("cases", "chargers"):
            MarkupRule.objects.update_or_create(
                category=categories[slug], is_active=True,
                defaults={"markup_pct": Decimal("25"), "min_margin_uzs": 20_000, "rounding_step_uzs": 1000},
            )
        GiftPolicy.objects.get_or_create(
            name="Смартфоны: подарок до 150 000 сум", category=categories["smartphones"],
            defaults={"budget_pct_of_net_margin": Decimal("15"), "budget_cap_uzs": 150_000},
        )
