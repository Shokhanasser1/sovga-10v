"""Данные демо-каталога для seed_demo: категории, бренды, товары с описаниями ru/uz, склад и наценки.

Характеристики — по данным производителей; цены (себестоимость в $) — учебные.
"""

from decimal import Decimal

from apps.catalog.models import AttributeDefinition

T = AttributeDefinition.Type
L = AttributeDefinition.Level
C = AttributeDefinition.Comparison
DEMO_MXIK = "08517001001000000"

COLORS = ["black", "white", "blue", "green", "titanium", "grey", "silver", "gold", "orange", "purple", "pink",
          "yellow"]

# code, ru, uz, type, unit, level, axis, facet, comparison, enum
STORAGE = ("storage_gb", "Память", "Xotira", T.NUMBER, "ГБ", L.VARIANT, True, True, C.HIGHER_BETTER, [])
COLOR = ("color", "Цвет", "Rang", T.ENUM, "", L.VARIANT, True, True, C.NONE, COLORS)
OUTPUT_W = ("output_w", "Мощность", "Quvvat", T.NUMBER, "Вт", L.MODEL, False, True, C.HIGHER_BETTER, [])
WEIGHT = ("weight_g", "Вес", "Ogʻirlik", T.NUMBER, "г", L.MODEL, False, False, C.LOWER_BETTER, [])

PHONE_ATTRIBUTES = [
    STORAGE,
    COLOR,
    ("sim", "SIM", "SIM", T.ENUM, "", L.VARIANT, True, True, C.NONE, ["nano_esim", "esim_only", "dual_sim"]),
    ("ram_gb", "Оперативная память", "Operativ xotira", T.NUMBER, "ГБ", L.MODEL, False, True, C.HIGHER_BETTER, []),
    ("screen_in", "Экран", "Ekran", T.NUMBER, "″", L.MODEL, False, False, C.NONE, []),
    ("chipset", "Процессор", "Protsessor", T.TEXT, "", L.MODEL, False, False, C.NONE, []),
    ("battery_mah", "Аккумулятор", "Batareya", T.NUMBER, "мА·ч", L.MODEL, False, False, C.HIGHER_BETTER, []),
    ("max_charge_w", "Быстрая зарядка", "Tez quvvatlash", T.NUMBER, "Вт", L.MODEL, False, False,
     C.HIGHER_BETTER, []),
    ("charge_port", "Разъём", "Ulagich", T.ENUM, "", L.MODEL, False, True, C.NONE, ["usb-c", "lightning"]),
    ("nfc", "NFC", "NFC", T.BOOL, "", L.MODEL, False, True, C.NONE, []),
    WEIGHT,
]
TABLET_ATTRIBUTES = [row for row in PHONE_ATTRIBUTES if row[0] in (
    "storage_gb", "color", "ram_gb", "screen_in", "chipset", "battery_mah", "weight_g"
)]
WATCH_ATTRIBUTES = [
    ("size_mm", "Размер корпуса", "Korpus oʻlchami", T.NUMBER, "мм", L.VARIANT, True, True, C.NONE, []),
    COLOR,
    ("battery_days", "Автономность", "Avtonomlik", T.NUMBER, "дн.", L.MODEL, False, False, C.HIGHER_BETTER, []),
    ("nfc", "NFC", "NFC", T.BOOL, "", L.MODEL, False, True, C.NONE, []),
]
HEADPHONE_ATTRIBUTES = [
    COLOR,
    ("form", "Тип", "Turi", T.ENUM, "", L.MODEL, False, True, C.NONE, ["in_ear", "on_ear", "over_ear"]),
    ("anc", "Шумоподавление", "Shovqin bostirish", T.BOOL, "", L.MODEL, False, True, C.NONE, []),
    ("battery_h", "Время работы", "Ishlash vaqti", T.NUMBER, "ч", L.MODEL, False, False, C.HIGHER_BETTER, []),
]
CASE_ATTRIBUTES = [("color", "Цвет", "Rang", T.ENUM, "", L.VARIANT, True, True, C.NONE, ["black", "white", "clear"])]
GLASS_ATTRIBUTES = [
    ("pack_qty", "В комплекте", "Toʻplamda", T.NUMBER, "шт.", L.MODEL, False, False, C.HIGHER_BETTER, []),
]
CHARGER_ATTRIBUTES = [
    OUTPUT_W,
    ("connector", "Разъём", "Ulagich", T.ENUM, "", L.MODEL, False, True, C.NONE, ["usb-c", "lightning"]),
]
POWER_BANK_ATTRIBUTES = [
    ("capacity_mah", "Ёмкость", "Sigʻim", T.NUMBER, "мА·ч", L.MODEL, False, True, C.HIGHER_BETTER, []),
    OUTPUT_W,
    WEIGHT,
]

CATEGORIES = [
    # slug, ru, uz, serialized (IMEI), attributes
    ("smartphones", "Смартфоны", "Smartfonlar", True, PHONE_ATTRIBUTES),
    ("tablets", "Планшеты", "Planshetlar", True, TABLET_ATTRIBUTES),
    ("cases", "Чехлы", "Gʻiloflar", False, CASE_ATTRIBUTES),
    ("chargers", "Зарядные устройства", "Quvvatlagichlar", False, CHARGER_ATTRIBUTES),
    ("headphones", "Наушники", "Quloqchinlar", False, HEADPHONE_ATTRIBUTES),
    ("smartwatches", "Смарт-часы", "Aqlli soatlar", False, WATCH_ATTRIBUTES),
    ("screen-protectors", "Защитные стекла", "Himoya oynalari", False, GLASS_ATTRIBUTES),
    ("power-banks", "Внешние аккумуляторы", "Powerbanklar", False, POWER_BANK_ATTRIBUTES),
]
ACCESSORY_CATEGORIES = {"cases", "chargers", "headphones", "screen-protectors", "power-banks"}

BRANDS = [("apple", "Apple"), ("samsung", "Samsung"), ("xiaomi", "Xiaomi"), ("honor", "Honor"), ("sony", "Sony"),
          ("jbl", "JBL"), ("anker", "Anker"), ("baseus", "Baseus"), ("ugreen", "Ugreen"), ("spigen", "Spigen")]


def phone(storage: int, color: str, sim: str = "nano_esim") -> dict:
    return {"storage_gb": storage, "color": color, "sim": sim}


def tablet(storage: int, color: str) -> dict:
    return {"storage_gb": storage, "color": color}


# slug, category, brand, ru, uz, attributes, variants: (sku, axes, cost_usd)
DEVICES = [
    ("iphone-17-pro-max", "smartphones", "apple", "iPhone 17 Pro Max", "iPhone 17 Pro Max",
     {"ram_gb": 12, "screen_in": 6.9, "chipset": "A19 Pro", "battery_mah": 4823, "max_charge_w": 40,
      "charge_port": "usb-c", "nfc": True, "weight_g": 231},
     [("IP17PM-256-ORG", phone(256, "orange"), "1300"), ("IP17PM-256-BLU", phone(256, "blue"), "1300"),
      ("IP17PM-512-SLV", phone(512, "silver"), "1480"),
      ("IP17PM-256-US", phone(256, "blue", "esim_only"), "1240")]),
    ("iphone-17-pro", "smartphones", "apple", "iPhone 17 Pro", "iPhone 17 Pro",
     {"ram_gb": 12, "screen_in": 6.3, "chipset": "A19 Pro", "battery_mah": 3988, "max_charge_w": 40,
      "charge_port": "usb-c", "nfc": True, "weight_g": 204},
     [("IP17P-256-ORG", phone(256, "orange"), "1150"), ("IP17P-256-BLU", phone(256, "blue"), "1150"),
      ("IP17P-512-SLV", phone(512, "silver"), "1330")]),
    ("iphone-air", "smartphones", "apple", "iPhone Air", "iPhone Air",
     {"ram_gb": 12, "screen_in": 6.5, "chipset": "A19 Pro", "battery_mah": 3149, "max_charge_w": 20,
      "charge_port": "usb-c", "nfc": True, "weight_g": 165},
     [("IPAIR-256-BLU", phone(256, "blue", "esim_only"), "980"),
      ("IPAIR-256-BLK", phone(256, "black", "esim_only"), "980"),
      ("IPAIR-512-GLD", phone(512, "gold", "esim_only"), "1150")]),
    ("iphone-17", "smartphones", "apple", "iPhone 17", "iPhone 17",
     {"ram_gb": 8, "screen_in": 6.3, "chipset": "A19", "battery_mah": 3692, "max_charge_w": 40,
      "charge_port": "usb-c", "nfc": True, "weight_g": 177},
     [("IP17-256-BLK", phone(256, "black"), "830"), ("IP17-256-PRP", phone(256, "purple"), "830"),
      ("IP17-256-GRN", phone(256, "green"), "830"), ("IP17-512-BLU", phone(512, "blue"), "1000")]),
    ("iphone-16-pro", "smartphones", "apple", "iPhone 16 Pro", "iPhone 16 Pro",
     {"ram_gb": 8, "screen_in": 6.3, "chipset": "A18 Pro", "battery_mah": 3582, "max_charge_w": 30,
      "charge_port": "usb-c", "nfc": True, "weight_g": 199},
     [("IP16P-128-BLK", phone(128, "black"), "950"), ("IP16P-256-BLK", phone(256, "black"), "1050"),
      ("IP16P-256-TIT", phone(256, "titanium"), "1060"), ("IP16P-512-TIT", phone(512, "titanium"), "1250"),
      # Американская версия: Apple продаёт её только с eSIM — на карточке будет предупреждение
      ("IP16P-256-US", phone(256, "black", "esim_only"), "990")]),
    ("iphone-16", "smartphones", "apple", "iPhone 16", "iPhone 16",
     {"ram_gb": 8, "screen_in": 6.1, "chipset": "A18", "battery_mah": 3561, "max_charge_w": 20,
      "charge_port": "usb-c", "nfc": True, "weight_g": 170},
     [("IP16-128-BLK", phone(128, "black"), "700"), ("IP16-128-PNK", phone(128, "pink"), "700"),
      ("IP16-256-BLU", phone(256, "blue"), "800")]),
    ("iphone-16e", "smartphones", "apple", "iPhone 16e", "iPhone 16e",
     {"ram_gb": 8, "screen_in": 6.1, "chipset": "A18", "battery_mah": 4005, "max_charge_w": 20,
      "charge_port": "usb-c", "nfc": True, "weight_g": 167},
     [("IP16E-128-BLK", phone(128, "black"), "560"), ("IP16E-128-WHT", phone(128, "white"), "560"),
      ("IP16E-256-BLK", phone(256, "black"), "660")]),
    ("iphone-15", "smartphones", "apple", "iPhone 15", "iPhone 15",
     {"ram_gb": 6, "screen_in": 6.1, "chipset": "A16 Bionic", "battery_mah": 3349, "max_charge_w": 20,
      "charge_port": "usb-c", "nfc": True, "weight_g": 171},
     [("IP15-128-BLK", phone(128, "black"), "650"), ("IP15-128-BLU", phone(128, "blue"), "650"),
      ("IP15-256-BLK", phone(256, "black"), "750")]),
    ("galaxy-s25-ultra", "smartphones", "samsung", "Galaxy S25 Ultra", "Galaxy S25 Ultra",
     {"ram_gb": 12, "screen_in": 6.9, "chipset": "Snapdragon 8 Elite", "battery_mah": 5000,
      "max_charge_w": 45, "charge_port": "usb-c", "nfc": True, "weight_g": 218},
     [("S25U-256-BLK", phone(256, "black", "dual_sim"), "1000"),
      ("S25U-512-TIT", phone(512, "titanium", "dual_sim"), "1150")]),
    ("galaxy-s25", "smartphones", "samsung", "Galaxy S25", "Galaxy S25",
     {"ram_gb": 12, "screen_in": 6.2, "chipset": "Snapdragon 8 Elite", "battery_mah": 4000, "max_charge_w": 25,
      "charge_port": "usb-c", "nfc": True, "weight_g": 162},
     [("S25-128-BLU", phone(128, "blue", "dual_sim"), "680"), ("S25-256-BLU", phone(256, "blue", "dual_sim"), "730"),
      ("S25-256-SLV", phone(256, "silver", "dual_sim"), "730")]),
    ("galaxy-s25-edge", "smartphones", "samsung", "Galaxy S25 Edge", "Galaxy S25 Edge",
     {"ram_gb": 12, "screen_in": 6.7, "chipset": "Snapdragon 8 Elite", "battery_mah": 3900, "max_charge_w": 25,
      "charge_port": "usb-c", "nfc": True, "weight_g": 163},
     [("S25E-256-BLK", phone(256, "black", "dual_sim"), "850"),
      ("S25E-256-SLV", phone(256, "silver", "dual_sim"), "850")]),
    ("galaxy-z-flip7", "smartphones", "samsung", "Galaxy Z Flip7", "Galaxy Z Flip7",
     {"ram_gb": 12, "screen_in": 6.9, "chipset": "Exynos 2500", "battery_mah": 4300, "max_charge_w": 25,
      "charge_port": "usb-c", "nfc": True, "weight_g": 188},
     [("ZFLIP7-256-BLU", phone(256, "blue", "dual_sim"), "880"),
      ("ZFLIP7-512-BLK", phone(512, "black", "dual_sim"), "980")]),
    ("galaxy-z-fold7", "smartphones", "samsung", "Galaxy Z Fold7", "Galaxy Z Fold7",
     {"ram_gb": 12, "screen_in": 8.0, "chipset": "Snapdragon 8 Elite", "battery_mah": 4400, "max_charge_w": 25,
      "charge_port": "usb-c", "nfc": True, "weight_g": 215},
     [("ZFOLD7-256-BLU", phone(256, "blue", "dual_sim"), "1550"),
      ("ZFOLD7-512-SLV", phone(512, "silver", "dual_sim"), "1700")]),
    ("galaxy-a56", "smartphones", "samsung", "Galaxy A56", "Galaxy A56",
     {"ram_gb": 8, "screen_in": 6.7, "chipset": "Exynos 1580", "battery_mah": 5000, "max_charge_w": 45,
      "charge_port": "usb-c", "nfc": True, "weight_g": 198},
     [("A56-128-BLK", phone(128, "black", "dual_sim"), "330"), ("A56-256-GRN", phone(256, "green", "dual_sim"), "380")]),
    ("galaxy-a36", "smartphones", "samsung", "Galaxy A36", "Galaxy A36",
     {"ram_gb": 8, "screen_in": 6.7, "chipset": "Snapdragon 6 Gen 3", "battery_mah": 5000, "max_charge_w": 45,
      "charge_port": "usb-c", "nfc": True, "weight_g": 195},
     [("A36-128-BLK", phone(128, "black", "dual_sim"), "270"),
      ("A36-256-PRP", phone(256, "purple", "dual_sim"), "310")]),
    ("galaxy-a16", "smartphones", "samsung", "Galaxy A16", "Galaxy A16",
     {"ram_gb": 6, "screen_in": 6.7, "chipset": "Exynos 1330", "battery_mah": 5000, "max_charge_w": 25,
      "charge_port": "usb-c", "nfc": True, "weight_g": 200},
     [("A16-128-BLK", phone(128, "black", "dual_sim"), "160"), ("A16-128-GRY", phone(128, "grey", "dual_sim"), "160")]),
    ("xiaomi-15", "smartphones", "xiaomi", "Xiaomi 15", "Xiaomi 15",
     {"ram_gb": 12, "screen_in": 6.36, "chipset": "Snapdragon 8 Elite", "battery_mah": 5240, "max_charge_w": 90,
      "charge_port": "usb-c", "nfc": True, "weight_g": 191},
     [("X15-256-BLK", phone(256, "black", "dual_sim"), "720"), ("X15-512-WHT", phone(512, "white", "dual_sim"), "820"),
      ("X15-512-GRN", phone(512, "green", "dual_sim"), "820")]),
    ("redmi-note-14-pro", "smartphones", "xiaomi", "Redmi Note 14 Pro", "Redmi Note 14 Pro",
     {"ram_gb": 8, "screen_in": 6.67, "chipset": "Dimensity 7300", "battery_mah": 5110, "max_charge_w": 45,
      "charge_port": "usb-c", "nfc": True, "weight_g": 190},
     [("RN14P-256-BLK", phone(256, "black", "dual_sim"), "260"),
      ("RN14P-256-BLU", phone(256, "blue", "dual_sim"), "260")]),
    ("redmi-note-14", "smartphones", "xiaomi", "Redmi Note 14", "Redmi Note 14",
     {"ram_gb": 8, "screen_in": 6.67, "chipset": "Helio G99-Ultra", "battery_mah": 5500, "max_charge_w": 33,
      "charge_port": "usb-c", "nfc": True, "weight_g": 196},
     [("RN14-256-BLK", phone(256, "black", "dual_sim"), "185"),
      ("RN14-256-PRP", phone(256, "purple", "dual_sim"), "185")]),
    ("redmi-14c", "smartphones", "xiaomi", "Redmi 14C", "Redmi 14C",
     {"ram_gb": 4, "screen_in": 6.88, "chipset": "Helio G81-Ultra", "battery_mah": 5160, "max_charge_w": 18,
      "charge_port": "usb-c", "nfc": False, "weight_g": 211},
     [("R14C-128-BLK", phone(128, "black", "dual_sim"), "105"),
      ("R14C-128-GRN", phone(128, "green", "dual_sim"), "105")]),
    ("poco-x7-pro", "smartphones", "xiaomi", "POCO X7 Pro", "POCO X7 Pro",
     {"ram_gb": 12, "screen_in": 6.67, "chipset": "Dimensity 8400-Ultra", "battery_mah": 6000, "max_charge_w": 90,
      "charge_port": "usb-c", "nfc": True, "weight_g": 195},
     [("PX7P-256-BLK", phone(256, "black", "dual_sim"), "330"),
      ("PX7P-512-YLW", phone(512, "yellow", "dual_sim"), "380")]),
    ("honor-400", "smartphones", "honor", "Honor 400", "Honor 400",
     {"ram_gb": 12, "screen_in": 6.55, "chipset": "Snapdragon 7 Gen 4", "battery_mah": 5300, "max_charge_w": 66,
      "charge_port": "usb-c", "nfc": True, "weight_g": 184},
     [("H400-256-BLK", phone(256, "black", "dual_sim"), "420"), ("H400-512-GLD", phone(512, "gold", "dual_sim"), "480")]),
    ("honor-x9c", "smartphones", "honor", "Honor X9c", "Honor X9c",
     {"ram_gb": 8, "screen_in": 6.78, "chipset": "Snapdragon 6 Gen 1", "battery_mah": 6600, "max_charge_w": 66,
      "charge_port": "usb-c", "nfc": True, "weight_g": 189},
     [("HX9C-256-BLK", phone(256, "black", "dual_sim"), "290"),
      ("HX9C-256-PRP", phone(256, "purple", "dual_sim"), "290")]),

    ("ipad-air-11", "tablets", "apple", "iPad Air 11", "iPad Air 11",
     {"ram_gb": 8, "screen_in": 11, "chipset": "M2", "battery_mah": 7606, "weight_g": 462},
     [("IPAD-AIR-128-BLU", tablet(128, "blue"), "600"), ("IPAD-AIR-256-GRY", tablet(256, "grey"), "700")]),
    ("ipad-11-a16", "tablets", "apple", "iPad 11 (A16)", "iPad 11 (A16)",
     {"ram_gb": 6, "screen_in": 11, "chipset": "A16", "battery_mah": 7606, "weight_g": 477},
     [("IPAD11-128-BLU", tablet(128, "blue"), "380"), ("IPAD11-128-PNK", tablet(128, "pink"), "380"),
      ("IPAD11-128-YLW", tablet(128, "yellow"), "380"), ("IPAD11-256-SLV", tablet(256, "silver"), "470")]),
    ("ipad-mini-a17-pro", "tablets", "apple", "iPad mini (A17 Pro)", "iPad mini (A17 Pro)",
     {"ram_gb": 8, "screen_in": 8.3, "chipset": "A17 Pro", "battery_mah": 5078, "weight_g": 293},
     [("IPADMINI-128-GRY", tablet(128, "grey"), "490"), ("IPADMINI-256-PRP", tablet(256, "purple"), "590")]),
    ("galaxy-tab-s10-fe", "tablets", "samsung", "Galaxy Tab S10 FE", "Galaxy Tab S10 FE",
     {"ram_gb": 8, "screen_in": 10.9, "chipset": "Exynos 1580", "battery_mah": 8000, "weight_g": 497},
     [("TABS10FE-128-GRY", tablet(128, "grey"), "420"), ("TABS10FE-128-BLU", tablet(128, "blue"), "420")]),
    ("galaxy-tab-a9-plus", "tablets", "samsung", "Galaxy Tab A9+", "Galaxy Tab A9+",
     {"ram_gb": 8, "screen_in": 11, "chipset": "Snapdragon 695", "battery_mah": 7040, "weight_g": 480},
     [("TABA9P-128-GRY", tablet(128, "grey"), "190"), ("TABA9P-128-SLV", tablet(128, "silver"), "190")]),
    ("xiaomi-pad-7", "tablets", "xiaomi", "Xiaomi Pad 7", "Xiaomi Pad 7",
     {"ram_gb": 8, "screen_in": 11.2, "chipset": "Snapdragon 7+ Gen 3", "battery_mah": 8850, "weight_g": 500},
     [("XPAD7-128-GRY", tablet(128, "grey"), "320"), ("XPAD7-256-BLU", tablet(256, "blue"), "360"),
      ("XPAD7-256-GRN", tablet(256, "green"), "360")]),
    ("redmi-pad-2", "tablets", "xiaomi", "Redmi Pad 2", "Redmi Pad 2",
     {"ram_gb": 6, "screen_in": 11, "chipset": "Helio G100-Ultra", "battery_mah": 9000, "weight_g": 510},
     [("RPAD2-128-GRY", tablet(128, "grey"), "170"), ("RPAD2-128-GRN", tablet(128, "green"), "170")]),

    ("apple-watch-series-11", "smartwatches", "apple", "Apple Watch Series 11", "Apple Watch Series 11",
     {"battery_days": 1, "nfc": True},
     [("AW11-42-BLK", {"size_mm": 42, "color": "black"}, "340"), ("AW11-42-PNK", {"size_mm": 42, "color": "pink"}, "340"),
      ("AW11-46-BLK", {"size_mm": 46, "color": "black"}, "370"),
      ("AW11-46-SLV", {"size_mm": 46, "color": "silver"}, "370")]),
    ("apple-watch-se-3", "smartwatches", "apple", "Apple Watch SE 3", "Apple Watch SE 3",
     {"battery_days": 0.75, "nfc": True},
     [("AWSE3-40-BLK", {"size_mm": 40, "color": "black"}, "210"), ("AWSE3-44-WHT", {"size_mm": 44, "color": "white"}, "240")]),
    ("apple-watch-ultra-3", "smartwatches", "apple", "Apple Watch Ultra 3", "Apple Watch Ultra 3",
     {"battery_days": 1.75, "nfc": True},
     [("AWU3-49-TIT", {"size_mm": 49, "color": "titanium"}, "720"),
      ("AWU3-49-BLK", {"size_mm": 49, "color": "black"}, "720")]),
    ("galaxy-watch8", "smartwatches", "samsung", "Galaxy Watch8", "Galaxy Watch8",
     {"battery_days": 1.5, "nfc": True},
     [("GW8-40-GRY", {"size_mm": 40, "color": "grey"}, "250"), ("GW8-44-SLV", {"size_mm": 44, "color": "silver"}, "280")]),
    ("galaxy-watch8-classic", "smartwatches", "samsung", "Galaxy Watch8 Classic", "Galaxy Watch8 Classic",
     {"battery_days": 1.5, "nfc": True},
     [("GW8C-46-BLK", {"size_mm": 46, "color": "black"}, "380"), ("GW8C-46-WHT", {"size_mm": 46, "color": "white"}, "380")]),
    ("galaxy-watch-fe", "smartwatches", "samsung", "Galaxy Watch FE", "Galaxy Watch FE",
     {"battery_days": 1.5, "nfc": True},
     [("GWFE-40-BLK", {"size_mm": 40, "color": "black"}, "130"), ("GWFE-40-PNK", {"size_mm": 40, "color": "pink"}, "130"),
      ("GWFE-40-SLV", {"size_mm": 40, "color": "silver"}, "130")]),
    ("xiaomi-watch-s4", "smartwatches", "xiaomi", "Xiaomi Watch S4", "Xiaomi Watch S4",
     {"battery_days": 15, "nfc": True},
     [("XWS4-47-BLK", {"size_mm": 47, "color": "black"}, "120"), ("XWS4-47-SLV", {"size_mm": 47, "color": "silver"}, "120")]),

    ("airpods-pro-3", "headphones", "apple", "AirPods Pro 3", "AirPods Pro 3",
     {"form": "in_ear", "anc": True, "battery_h": 24}, [("AIRPODS-PRO-3", {"color": "white"}, "230")]),
    ("airpods-pro-2", "headphones", "apple", "AirPods Pro 2", "AirPods Pro 2",
     {"form": "in_ear", "anc": True, "battery_h": 30}, [("AIRPODS-PRO-2", {"color": "white"}, "190")]),
    ("airpods-4-anc", "headphones", "apple", "AirPods 4 с шумоподавлением", "Shovqin bostirishli AirPods 4",
     {"form": "in_ear", "anc": True, "battery_h": 30}, [("AIRPODS-4-ANC", {"color": "white"}, "160")]),
    ("galaxy-buds3-pro", "headphones", "samsung", "Galaxy Buds3 Pro", "Galaxy Buds3 Pro",
     {"form": "in_ear", "anc": True, "battery_h": 26},
     [("BUDS3P-SLV", {"color": "silver"}, "190"), ("BUDS3P-WHT", {"color": "white"}, "190")]),
    ("sony-wh-1000xm6", "headphones", "sony", "Sony WH-1000XM6", "Sony WH-1000XM6",
     {"form": "over_ear", "anc": True, "battery_h": 30},
     [("XM6-BLK", {"color": "black"}, "390"), ("XM6-SLV", {"color": "silver"}, "390"),
      ("XM6-BLU", {"color": "blue"}, "390")]),
    ("jbl-tune-520bt", "headphones", "jbl", "JBL Tune 520BT", "JBL Tune 520BT",
     {"form": "on_ear", "anc": False, "battery_h": 57},
     [("JBL520-BLK", {"color": "black"}, "38"), ("JBL520-WHT", {"color": "white"}, "38"),
      ("JBL520-BLU", {"color": "blue"}, "38"), ("JBL520-PRP", {"color": "purple"}, "38")]),
    ("redmi-buds-6-pro", "headphones", "xiaomi", "Redmi Buds 6 Pro", "Redmi Buds 6 Pro",
     {"form": "in_ear", "anc": True, "battery_h": 36},
     [("RBUDS6P-BLK", {"color": "black"}, "55"), ("RBUDS6P-WHT", {"color": "white"}, "55")]),

    ("charger-anker-30w", "chargers", "anker", "Зарядное устройство Anker 30 Вт USB-C",
     "Anker 30 Vt USB-C quvvatlagichi", {"output_w": 30, "connector": "usb-c"}, [("CHG-ANKER-30", {}, "12")]),
    ("charger-samsung-45w", "chargers", "samsung", "Зарядное устройство Samsung 45 Вт",
     "Samsung 45 Vt quvvatlagichi", {"output_w": 45, "connector": "usb-c"}, [("CHG-SAMSUNG-45", {}, "25")]),
    ("charger-apple-20w", "chargers", "apple", "Адаптер питания Apple 20 Вт USB-C",
     "Apple 20 Vt USB-C quvvat adapteri", {"output_w": 20, "connector": "usb-c"}, [("CHG-APPLE-20", {}, "14")]),
    ("charger-baseus-65w", "chargers", "baseus", "Зарядное устройство Baseus GaN 65 Вт",
     "Baseus GaN 65 Vt quvvatlagichi", {"output_w": 65, "connector": "usb-c"}, [("CHG-BASEUS-65", {}, "22")]),
    ("charger-ugreen-100w", "chargers", "ugreen", "Зарядное устройство Ugreen Nexode 100 Вт",
     "Ugreen Nexode 100 Vt quvvatlagichi", {"output_w": 100, "connector": "usb-c"}, [("CHG-UGREEN-100", {}, "45")]),

    ("powerbank-anker-10000", "power-banks", "anker", "Внешний аккумулятор Anker Nano 10000 мА·ч",
     "Anker Nano 10000 mA·soat powerbanki", {"capacity_mah": 10000, "output_w": 30, "weight_g": 215},
     [("PB-ANKER-10K", {}, "28")]),
    ("powerbank-xiaomi-20000", "power-banks", "xiaomi", "Внешний аккумулятор Xiaomi 20000 мА·ч",
     "Xiaomi 20000 mA·soat powerbanki", {"capacity_mah": 20000, "output_w": 22.5, "weight_g": 414},
     [("PB-XIAOMI-20K", {}, "22")]),
    ("powerbank-baseus-magnetic", "power-banks", "baseus", "Магнитный аккумулятор Baseus 10000 мА·ч",
     "Baseus magnitli powerbanki 10000 mA·soat", {"capacity_mah": 10000, "output_w": 20, "weight_g": 200},
     [("PB-BASEUS-MAG", {}, "26")]),
]

# Чехлы и стёкла: к какой модели, бренд, варианты (sku, axes, cost_usd), для стёкол — штук в комплекте
CASES = [
    ("iphone-16-pro", "iPhone 16 Pro", [("CASE-IP16P-BLK", "black", "9"), ("CASE-IP16P-CLR", "clear", "8")]),
    ("galaxy-s25-ultra", "Galaxy S25 Ultra", [("CASE-S25U-BLK", "black", "9")]),
    ("iphone-17-pro-max", "iPhone 17 Pro Max", [("CASE-IP17PM-BLK", "black", "10"), ("CASE-IP17PM-CLR", "clear", "9")]),
    ("iphone-17-pro", "iPhone 17 Pro", [("CASE-IP17P-BLK", "black", "10"), ("CASE-IP17P-CLR", "clear", "9")]),
    ("iphone-17", "iPhone 17", [("CASE-IP17-BLK", "black", "9"), ("CASE-IP17-CLR", "clear", "8")]),
    ("iphone-air", "iPhone Air", [("CASE-IPAIR-CLR", "clear", "9"), ("CASE-IPAIR-BLK", "black", "9")]),
    ("galaxy-s25", "Galaxy S25", [("CASE-S25-BLK", "black", "8"), ("CASE-S25-CLR", "clear", "7")]),
    ("galaxy-a56", "Galaxy A56", [("CASE-A56-BLK", "black", "6"), ("CASE-A56-CLR", "clear", "5")]),
]
GLASSES = [
    ("iphone-17-pro-max", "iPhone 17 Pro Max", "spigen", "Spigen", 2, "GLS-IP17PM", "6"),
    ("iphone-17-pro", "iPhone 17 Pro", "spigen", "Spigen", 2, "GLS-IP17P", "6"),
    ("iphone-17", "iPhone 17", "spigen", "Spigen", 2, "GLS-IP17", "5"),
    ("iphone-16-pro", "iPhone 16 Pro", "spigen", "Spigen", 2, "GLS-IP16P", "5"),
    ("galaxy-s25-ultra", "Galaxy S25 Ultra", "spigen", "Spigen", 2, "GLS-S25U", "7"),
    ("galaxy-a56", "Galaxy A56", "baseus", "Baseus", 1, "GLS-A56", "3"),
]


def case_slug(device: str) -> str:
    return f"case-{device}"


def glass_slug(device: str) -> str:
    return f"glass-{device}"


def _accessories() -> list[tuple]:
    rows = [
        (case_slug(device), "cases", "spigen", f"Чехол Spigen для {model}", f"{model} uchun Spigen gʻilofi", {},
         [(sku, {"color": color}, cost) for sku, color, cost in variants])
        for device, model, variants in CASES
    ]
    rows += [
        (glass_slug(device), "screen-protectors", brand, f"Защитное стекло {brand_name} для {model}",
         f"{model} uchun {brand_name} himoya oynasi", {"pack_qty": qty}, [(sku, {}, cost)])
        for device, model, brand, brand_name, qty, sku, cost in GLASSES
    ]
    return rows


PRODUCTS = DEVICES + _accessories()

DESCRIPTIONS = {
    "iphone-17-pro-max": (
        "Самый большой iPhone 2025 года: экран 6,9″ с частотой 120 Гц, процессор A19 Pro и алюминиевый корпус "
        "с испарительной камерой — телефон не перегревается в играх и при съёмке видео 4K. Три камеры по 48 Мп, "
        "включая телеобъектив с 8-кратным зумом оптического качества.\n\n"
        "Аккумулятора хватает на целый день активной работы, а адаптер на 40 Вт заряжает до 50% примерно "
        "за 20 минут.",
        "2025-yilning eng katta iPhone'i: 120 Gs chastotali 6,9″ ekran, A19 Pro protsessori va bugʻlanish kamerali "
        "alyuminiy korpus — oʻyinlarda va 4K video suratga olishda qizib ketmaydi. Uchta 48 Mp kamera, jumladan "
        "8 karra optik sifatli zumli telefoto.\n\n"
        "Batareya butun kunlik faol ishlashga yetadi, 40 Vt adapter esa taxminan 20 daqiqada 50% gacha "
        "quvvatlaydi.",
    ),
    "iphone-17-pro": (
        "Компактный флагман: те же процессор A19 Pro, три камеры по 48 Мп и корпус с испарительной камерой, "
        "что у Pro Max, но с экраном 6,3″ — удобно держать одной рукой.\n\n"
        "Экран ProMotion 120 Гц с яркостью до 3000 нит хорошо читается даже под ярким солнцем.",
        "Ixcham flagman: Pro Max'dagi kabi A19 Pro protsessori, uchta 48 Mp kamera va bugʻlanish kamerali korpus, "
        "lekin ekrani 6,3″ — bir qoʻlda ushlash qulay.\n\n"
        "3000 nitgacha yorqinlikdagi 120 Gs ProMotion ekrani yorqin quyosh ostida ham yaxshi koʻrinadi.",
    ),
    "iphone-air": (
        "Самый тонкий iPhone — 5,6 мм и 165 г, рамка из титана. Экран 6,5″ 120 Гц и процессор A19 Pro, "
        "как у старших моделей.\n\n"
        "iPhone Air работает только с eSIM: физическую SIM-карту вставить нельзя. Узбекские операторы выпускают "
        "eSIM в своих офисах.",
        "Eng yupqa iPhone — 5,6 mm va 165 g, titan ramka. Katta modellardagi kabi 120 Gs 6,5″ ekran va A19 Pro "
        "protsessori.\n\n"
        "iPhone Air faqat eSIM bilan ishlaydi: jismoniy SIM-kartani qoʻyib boʻlmaydi. Oʻzbekiston operatorlari "
        "eSIM'ni oʻz ofislarida chiqarib beradi.",
    ),
    "iphone-17": (
        "Базовый iPhone 17 впервые получил экран ProMotion 120 Гц с режимом Always-On, а память теперь "
        "от 256 ГБ. Процессор A19 и фронтальная камера 18 Мп с функцией Center Stage — кадр сам подстраивается "
        "под группу.\n\n"
        "Хороший выбор, если нужен новый iPhone без переплаты за Pro.",
        "Asosiy iPhone 17 ilk bor Always-On rejimli 120 Gs ProMotion ekranini oldi, xotira esa endi 256 GB dan "
        "boshlanadi. A19 protsessori va Center Stage funksiyali 18 Mp old kamera — kadr guruhga oʻzi moslashadi.\n\n"
        "Pro uchun ortiqcha toʻlamasdan yangi iPhone kerak boʻlsa — yaxshi tanlov.",
    ),
    "iphone-16-pro": (
        "Флагман 2024 года в титановом корпусе: экран 6,3″ 120 Гц, процессор A18 Pro и тройная камера "
        "с 5-кратным телеобъективом. Кнопка «Управление камерой» помогает снимать быстрее.\n\n"
        "Есть американская версия только с eSIM — она дешевле, но физическую SIM-карту в неё не вставить.",
        "2024-yilgi titan korpusdagi flagman: 120 Gs 6,3″ ekran, A18 Pro protsessori va 5 karra telefotoli uchlik "
        "kamera. «Kamerani boshqarish» tugmasi tezroq suratga olishga yordam beradi.\n\n"
        "Faqat eSIM bilan ishlaydigan Amerika versiyasi ham bor — u arzonroq, lekin unga jismoniy SIM-karta "
        "qoʻyib boʻlmaydi.",
    ),
    "iphone-16": (
        "iPhone 16 с процессором A18, кнопкой «Управление камерой» и основной камерой 48 Мп. Экран 6,1″, "
        "корпус из алюминия и стекла.\n\n"
        "Поддерживает MagSafe и заряжается через USB-C — подходит тот же кабель, что и для Android.",
        "A18 protsessori, «Kamerani boshqarish» tugmasi va 48 Mp asosiy kamerali iPhone 16. 6,1″ ekran, "
        "alyuminiy va shisha korpus.\n\n"
        "MagSafe'ni qoʻllab-quvvatlaydi va USB-C orqali quvvatlanadi — Android uchun ishlatiladigan kabel ham "
        "mos keladi.",
    ),
    "iphone-16e": (
        "Самый доступный iPhone в линейке: процессор A18, экран 6,1″ и камера 48 Мп с двукратным зумом "
        "без потери качества.\n\n"
        "Аккумулятор держит дольше, чем у iPhone 16, — до 26 часов видео.",
        "Qatordagi eng hamyonbop iPhone: A18 protsessori, 6,1″ ekran va sifatni yoʻqotmaydigan 2 karra zumli "
        "48 Mp kamera.\n\n"
        "Batareyasi iPhone 16 nikidan uzoqroq ishlaydi — 26 soatgacha video.",
    ),
    "iphone-15": (
        "iPhone 15 — проверенная модель с Dynamic Island, камерой 48 Мп и разъёмом USB-C. Процессор A16 Bionic "
        "уверенно справляется с любыми приложениями.\n\n"
        "Хороший вариант для первого iPhone или подарка.",
        "iPhone 15 — Dynamic Island, 48 Mp kamera va USB-C ulagichli sinalgan model. A16 Bionic protsessori "
        "har qanday ilovani bemalol tortadi.\n\n"
        "Birinchi iPhone yoki sovgʻa uchun yaxshi variant.",
    ),
    "galaxy-s25-ultra": (
        "Флагман Samsung с экраном 6,9″, процессором Snapdragon 8 Elite for Galaxy и встроенным пером S Pen. "
        "Камера 200 Мп и перископический зум 5×.\n\n"
        "Samsung обещает 7 лет обновлений Android — телефон прослужит долго.",
        "6,9″ ekranli, Snapdragon 8 Elite for Galaxy protsessorli va ichiga S Pen qalami oʻrnatilgan Samsung "
        "flagmani. 200 Mp kamera va 5× periskop zum.\n\n"
        "Samsung 7 yil Android yangilanishlarini vaʼda qiladi — telefon uzoq xizmat qiladi.",
    ),
    "galaxy-s25": (
        "Компактный Galaxy S25 с экраном 6,2″ и тем же процессором Snapdragon 8 Elite, что у Ultra. "
        "Тройная камера с телеобъективом 3×.\n\n"
        "Лёгкий — 162 г, удобно носить в кармане. 7 лет обновлений Android.",
        "6,2″ ekranli va Ultra'dagi kabi Snapdragon 8 Elite protsessorli ixcham Galaxy S25. 3× telefotoli "
        "uchlik kamera.\n\n"
        "Yengil — 162 g, choʻntakda olib yurish qulay. 7 yil Android yangilanishlari.",
    ),
    "galaxy-s25-edge": (
        "Самый тонкий Galaxy — 5,8 мм при экране 6,7″. Основная камера 200 Мп, как у Ultra, рамка из титана.\n\n"
        "Плата за тонкость — аккумулятор 3900 мА·ч: на день хватает, но заряжать придётся каждый вечер.",
        "Eng yupqa Galaxy — 6,7″ ekranda 5,8 mm. Ultra'dagi kabi 200 Mp asosiy kamera, titan ramka.\n\n"
        "Yupqalik evaziga batareya 3900 mA·soat: bir kunga yetadi, lekin har kech quvvatlash kerak boʻladi.",
    ),
    "galaxy-z-flip7": (
        "Раскладушка с большим внешним экраном 4,1″ — на нём можно отвечать на сообщения и снимать селфи "
        "на основную камеру 50 Мп. Внутренний экран 6,9″.\n\n"
        "Процессор Exynos 2500 и аккумулятор 4300 мА·ч — самый ёмкий в истории Flip.",
        "4,1″ katta tashqi ekranli buklanadigan telefon — unda xabarlarga javob berish va 50 Mp asosiy kamerada "
        "selfi olish mumkin. Ichki ekran 6,9″.\n\n"
        "Exynos 2500 protsessori va 4300 mA·soat batareya — Flip tarixidagi eng sigʻimlisi.",
    ),
    "galaxy-z-fold7": (
        "Телефон, который раскрывается в планшет с экраном 8″. В сложенном виде — 8,9 мм и 215 г, "
        "как обычный флагман.\n\n"
        "Камера 200 Мп и Snapdragon 8 Elite. Удобно работать с двумя приложениями рядом.",
        "8″ ekranli planshetga ochiladigan telefon. Buklangan holda — 8,9 mm va 215 g, oddiy flagman kabi.\n\n"
        "200 Mp kamera va Snapdragon 8 Elite. Ikki ilova bilan yonma-yon ishlash qulay.",
    ),
    "galaxy-a56": (
        "Galaxy A56 — металлическая рамка, экран AMOLED 6,7″ 120 Гц и быстрая зарядка 45 Вт. "
        "Защита от воды IP67.\n\n"
        "6 лет обновлений Android — редкость для среднего класса.",
        "Galaxy A56 — metall ramka, 120 Gs 6,7″ AMOLED ekran va 45 Vt tez quvvatlash. IP67 suvdan himoya.\n\n"
        "6 yil Android yangilanishlari — oʻrta sinf uchun kamdan-kam uchraydi.",
    ),
    "galaxy-a36": (
        "Экран AMOLED 6,7″ 120 Гц, процессор Snapdragon 6 Gen 3 и зарядка 45 Вт. Защита IP67 от воды и пыли.\n\n"
        "Как и A56, получит 6 лет обновлений Android.",
        "120 Gs 6,7″ AMOLED ekran, Snapdragon 6 Gen 3 protsessori va 45 Vt quvvatlash. Suv va changdan IP67 "
        "himoya.\n\n"
        "A56 kabi 6 yil Android yangilanishlarini oladi.",
    ),
    "galaxy-a16": (
        "Недорогой Galaxy с большим экраном AMOLED 6,7″ и аккумулятором 5000 мА·ч на два дня.\n\n"
        "Samsung обещает 6 лет обновлений Android — для бюджетного телефона это много.",
        "6,7″ katta AMOLED ekranli va ikki kunga yetadigan 5000 mA·soat batareyali arzon Galaxy.\n\n"
        "Samsung 6 yil Android yangilanishlarini vaʼda qiladi — byudjet telefon uchun bu koʻp.",
    ),
    "xiaomi-15": (
        "Компактный флагман Xiaomi: экран 6,36″, Snapdragon 8 Elite и камеры, настроенные вместе с Leica. "
        "Аккумулятор 5240 мА·ч и зарядка 90 Вт.\n\n"
        "Мощный телефон, который помещается в любой карман.",
        "Ixcham Xiaomi flagmani: 6,36″ ekran, Snapdragon 8 Elite va Leica bilan birga sozlangan kameralar. "
        "5240 mA·soat batareya va 90 Vt quvvatlash.\n\n"
        "Har qanday choʻntakka sigʻadigan kuchli telefon.",
    ),
    "redmi-note-14-pro": (
        "Redmi Note 14 Pro — изогнутый экран AMOLED 6,67″, камера 200 Мп и защита IP68.\n\n"
        "Зарядка 45 Вт и аккумулятор 5110 мА·ч.",
        "Redmi Note 14 Pro — 6,67″ egilgan AMOLED ekran, 200 Mp kamera va IP68 himoya.\n\n"
        "45 Vt quvvatlash va 5110 mA·soat batareya.",
    ),
    "redmi-note-14": (
        "Экран AMOLED 6,67″ 120 Гц, камера 108 Мп и аккумулятор 5500 мА·ч. Процессор Helio G99-Ultra.\n\n"
        "Один из самых популярных недорогих телефонов.",
        "120 Gs 6,67″ AMOLED ekran, 108 Mp kamera va 5500 mA·soat batareya. Helio G99-Ultra protsessori.\n\n"
        "Eng ommabop arzon telefonlardan biri.",
    ),
    "redmi-14c": (
        "Большой экран 6,88″ 120 Гц, камера 50 Мп и аккумулятор 5160 мА·ч по доступной цене.\n\n"
        "Подойдёт как первый смартфон или запасной телефон.",
        "Hamyonbop narxda 120 Gs 6,88″ katta ekran, 50 Mp kamera va 5160 mA·soat batareya.\n\n"
        "Birinchi smartfon yoki zaxira telefon sifatida mos keladi.",
    ),
    "poco-x7-pro": (
        "POCO X7 Pro — мощный процессор Dimensity 8400-Ultra по цене среднего класса, экран AMOLED 6,67″ "
        "и аккумулятор 6000 мА·ч.\n\n"
        "Зарядка 90 Вт: от нуля до 100% меньше чем за час. Хороший выбор для игр.",
        "POCO X7 Pro — oʻrta sinf narxida kuchli Dimensity 8400-Ultra protsessori, 6,67″ AMOLED ekran va "
        "6000 mA·soat batareya.\n\n"
        "90 Vt quvvatlash: noldan 100% gacha bir soatdan kamroq. Oʻyinlar uchun yaxshi tanlov.",
    ),
    "honor-400": (
        "Honor 400 — камера 200 Мп, экран AMOLED 6,55″ с яркостью до 5000 нит и аккумулятор 5300 мА·ч.\n\n"
        "Зарядка 66 Вт и защита от воды IP65.",
        "Honor 400 — 200 Mp kamera, 5000 nitgacha yorqinlikdagi 6,55″ AMOLED ekran va 5300 mA·soat batareya.\n\n"
        "66 Vt quvvatlash va IP65 suvdan himoya.",
    ),
    "honor-x9c": (
        "Прочный Honor X9c: экран 6,78″ выдерживает падения, корпус защищён от воды. Аккумулятор 6600 мА·ч — "
        "до двух дней работы.\n\n"
        "Камера 108 Мп со стабилизацией.",
        "Mustahkam Honor X9c: 6,78″ ekran tushishlarga bardosh beradi, korpus suvdan himoyalangan. "
        "6600 mA·soat batareya — ikki kungacha ishlaydi.\n\n"
        "Stabilizatsiyali 108 Mp kamera.",
    ),
    "ipad-air-11": (
        "iPad Air 11″ с процессором M2 — хватит и для учёбы, и для рисования, и для монтажа видео. "
        "Поддерживает Apple Pencil Pro и клавиатуру Magic Keyboard.\n\n"
        "Весит 462 г — легко носить в рюкзаке.",
        "M2 protsessorli iPad Air 11″ — oʻqish, rasm chizish va video montaj uchun yetarli. Apple Pencil Pro va "
        "Magic Keyboard klaviaturasini qoʻllab-quvvatlaydi.\n\n"
        "462 g — ryukzakda olib yurish oson.",
    ),
    "ipad-11-a16": (
        "Самый доступный iPad: экран 11″, процессор A16 и память от 128 ГБ. Четыре ярких цвета.\n\n"
        "Хороший планшет для учёбы, фильмов и видеозвонков.",
        "Eng hamyonbop iPad: 11″ ekran, A16 protsessori va 128 GB dan xotira. Toʻrtta yorqin rang.\n\n"
        "Oʻqish, filmlar va video qoʻngʻiroqlar uchun yaxshi planshet.",
    ),
    "ipad-mini-a17-pro": (
        "iPad mini с экраном 8,3″ помещается в одной руке. Процессор A17 Pro и поддержка Apple Pencil Pro.\n\n"
        "Удобно читать, вести конспекты и брать в дорогу.",
        "8,3″ ekranli iPad mini bir qoʻlga sigʻadi. A17 Pro protsessori va Apple Pencil Pro "
        "qoʻllab-quvvatlanadi.\n\n"
        "Oʻqish, konspekt yozish va safarga olish qulay.",
    ),
    "galaxy-tab-s10-fe": (
        "Планшет Samsung с экраном 10,9″, пером S Pen в комплекте и защитой IP68.\n\n"
        "Аккумулятор 8000 мА·ч и зарядка 45 Вт.",
        "10,9″ ekranli, toʻplamda S Pen qalami bor va IP68 himoyali Samsung planshet.\n\n"
        "8000 mA·soat batareya va 45 Vt quvvatlash.",
    ),
    "galaxy-tab-a9-plus": (
        "Недорогой планшет с экраном 11″ 90 Гц и четырьмя динамиками.\n\n"
        "Подойдёт для видео, онлайн-уроков и детских игр.",
        "90 Gs 11″ ekranli va toʻrtta dinamikli arzon planshet.\n\n"
        "Video, onlayn darslar va bolalar oʻyinlari uchun mos.",
    ),
    "xiaomi-pad-7": (
        "Экран 11,2″ 3,2K с частотой 144 Гц и процессор Snapdragon 7+ Gen 3. Аккумулятор 8850 мА·ч.\n\n"
        "С клавиатурой Xiaomi превращается в ноутбук для учёбы.",
        "144 Gs 3,2K 11,2″ ekran va Snapdragon 7+ Gen 3 protsessori. 8850 mA·soat batareya.\n\n"
        "Xiaomi klaviaturasi bilan oʻqish uchun noutbukka aylanadi.",
    ),
    "redmi-pad-2": (
        "Redmi Pad 2 — экран 11″ 2,5K и аккумулятор 9000 мА·ч, которого хватает на несколько дней.\n\n"
        "Доступный планшет для всей семьи.",
        "Redmi Pad 2 — 11″ 2,5K ekran va bir necha kunga yetadigan 9000 mA·soat batareya.\n\n"
        "Butun oila uchun hamyonbop planshet.",
    ),
    "apple-watch-series-11": (
        "Apple Watch Series 11 следят за пульсом, сном и тренировками и предупреждают о признаках высокого "
        "давления. Работают до 24 часов.\n\n"
        "Два размера корпуса — 42 и 46 мм. Работают только с iPhone.",
        "Apple Watch Series 11 puls, uyqu va mashgʻulotlarni kuzatadi, yuqori qon bosimi belgilari haqida "
        "ogohlantiradi. 24 soatgacha ishlaydi.\n\n"
        "Ikki korpus oʻlchami — 42 va 46 mm. Faqat iPhone bilan ishlaydi.",
    ),
    "apple-watch-se-3": (
        "Самые доступные Apple Watch: экран Always-On, отслеживание сна и тренировок.\n\n"
        "Хороший выбор для первых умных часов. Работают только с iPhone.",
        "Eng hamyonbop Apple Watch: Always-On ekran, uyqu va mashgʻulotlarni kuzatish.\n\n"
        "Birinchi aqlli soat uchun yaxshi tanlov. Faqat iPhone bilan ishlaydi.",
    ),
    "apple-watch-ultra-3": (
        "Титановые Apple Watch Ultra 3 для спорта и путешествий: самый большой экран Apple Watch, точный GPS "
        "и до 42 часов работы.\n\n"
        "Защита от воды до 100 м — подходят для плавания и дайвинга.",
        "Sport va sayohat uchun titan Apple Watch Ultra 3: Apple Watch'ning eng katta ekrani, aniq GPS va "
        "42 soatgacha ishlash.\n\n"
        "100 m gacha suvdan himoya — suzish va shoʻngʻish uchun mos.",
    ),
    "galaxy-watch8": (
        "Тонкие Galaxy Watch8 на Wear OS: пульс, сон, тренировки и подсказки ассистента Gemini прямо "
        "на запястье.\n\n"
        "Лучше всего работают с телефонами Samsung, подходят и к другим Android.",
        "Wear OS'dagi yupqa Galaxy Watch8: puls, uyqu, mashgʻulotlar va Gemini yordamchisi maslahatlari "
        "bilakda.\n\n"
        "Samsung telefonlari bilan eng yaxshi ishlaydi, boshqa Android'larga ham mos.",
    ),
    "galaxy-watch8-classic": (
        "Galaxy Watch8 Classic — классический корпус 46 мм с вращающимся безелем.\n\n"
        "Все функции Galaxy Watch8 и встроенная память для музыки.",
        "Galaxy Watch8 Classic — aylanadigan bezelli 46 mm klassik korpus.\n\n"
        "Galaxy Watch8 ning barcha funksiyalari va musiqa uchun ichki xotira.",
    ),
    "galaxy-watch-fe": (
        "Самые доступные Galaxy Watch: корпус 40 мм, экран с сапфировым стеклом, пульс, сон и более 100 видов "
        "тренировок.\n\n"
        "Работают с телефонами на Android, лучше всего — с Samsung.",
        "Eng hamyonbop Galaxy Watch: 40 mm korpus, safir shishali ekran, puls, uyqu va 100 dan ortiq mashgʻulot "
        "turi.\n\n"
        "Android telefonlar bilan ishlaydi, eng yaxshisi — Samsung bilan.",
    ),
    "xiaomi-watch-s4": (
        "Круглые часы Xiaomi с экраном AMOLED, металлическим корпусом 47 мм и до 15 дней работы.\n\n"
        "Работают с Android и iPhone через приложение Mi Fitness.",
        "AMOLED ekranli, 47 mm metall korpusli va 15 kungacha ishlaydigan dumaloq Xiaomi soati.\n\n"
        "Mi Fitness ilovasi orqali Android va iPhone bilan ishlaydi.",
    ),
    "airpods-pro-3": (
        "AirPods Pro 3 — шумоподавление сильнее, чем у прошлой модели, и датчик пульса для тренировок. "
        "Защита IP57.\n\n"
        "До 8 часов на одном заряде, до 24 часов с кейсом.",
        "AirPods Pro 3 — oldingi modeldan kuchliroq shovqin bostirish va mashgʻulotlar uchun puls sensori. "
        "IP57 himoya.\n\n"
        "Bir quvvatlashda 8 soatgacha, gʻilof bilan 24 soatgacha.",
    ),
    "airpods-pro-2": (
        "AirPods Pro 2 с активным шумоподавлением и прозрачным режимом. Кейс с USB-C и динамиком для поиска.\n\n"
        "До 30 часов вместе с кейсом.",
        "Faol shovqin bostirish va shaffof rejimli AirPods Pro 2. USB-C va qidirish dinamikli gʻilof.\n\n"
        "Gʻilof bilan birga 30 soatgacha.",
    ),
    "airpods-4-anc": (
        "AirPods 4 с активным шумоподавлением в открытом дизайне — без силиконовых насадок.\n\n"
        "Кейс заряжается через USB-C или без проводов. До 30 часов с кейсом.",
        "Ochiq dizayndagi faol shovqin bostirishli AirPods 4 — silikon uchliklarsiz.\n\n"
        "Gʻilof USB-C orqali yoki simsiz quvvatlanadi. Gʻilof bilan 30 soatgacha.",
    ),
    "galaxy-buds3-pro": (
        "Galaxy Buds3 Pro с адаптивным шумоподавлением и двумя динамиками в каждом наушнике.\n\n"
        "Лучше всего звучат с телефонами Samsung. До 26 часов с кейсом.",
        "Moslashuvchan shovqin bostirishli va har bir quloqchinda ikkita dinamikli Galaxy Buds3 Pro.\n\n"
        "Samsung telefonlari bilan eng yaxshi yangraydi. Gʻilof bilan 26 soatgacha.",
    ),
    "sony-wh-1000xm6": (
        "Полноразмерные наушники Sony с одним из лучших шумоподавлений: в самолёте и метро слышно только "
        "музыку.\n\n"
        "До 30 часов с включённым шумоподавлением, складываются в компактный кейс.",
        "Eng yaxshi shovqin bostirishlardan biriga ega Sony toʻliq oʻlchamli quloqchinlari: samolyot va metroda "
        "faqat musiqa eshitiladi.\n\n"
        "Shovqin bostirish yoqilganda 30 soatgacha, ixcham gʻilofga buklanadi.",
    ),
    "jbl-tune-520bt": (
        "Лёгкие накладные наушники JBL с фирменным звуком Pure Bass и временем работы до 57 часов.\n\n"
        "Пять минут зарядки — ещё три часа музыки.",
        "Pure Bass ovozli va 57 soatgacha ishlaydigan yengil JBL quloqchinlari.\n\n"
        "Besh daqiqa quvvatlash — yana uch soat musiqa.",
    ),
    "redmi-buds-6-pro": (
        "Redmi Buds 6 Pro — шумоподавление до 55 дБ и три динамика в каждом наушнике по цене бюджетной "
        "модели.\n\n"
        "До 36 часов с кейсом.",
        "Redmi Buds 6 Pro — 55 dB gacha shovqin bostirish va har bir quloqchinda uchta dinamik, byudjet model "
        "narxida.\n\n"
        "Gʻilof bilan 36 soatgacha.",
    ),
    "charger-anker-30w": (
        "Компактная зарядка Anker на 30 Вт с технологией GaN — меньше обычного адаптера. Быстро заряжает "
        "iPhone, Galaxy и AirPods.\n\n"
        "Кабель USB-C в комплект не входит.",
        "GaN texnologiyali ixcham Anker 30 Vt quvvatlagichi — oddiy adapterdan kichikroq. iPhone, Galaxy va "
        "AirPods'ni tez quvvatlaydi.\n\n"
        "USB-C kabel toʻplamga kirmaydi.",
    ),
    "charger-samsung-45w": (
        "Оригинальная зарядка Samsung Super Fast Charging 2.0 на 45 Вт — максимальная скорость для Galaxy "
        "S25 Ultra и A56.\n\n"
        "Кабель USB-C в комплекте.",
        "Samsung Super Fast Charging 2.0 original 45 Vt quvvatlagichi — Galaxy S25 Ultra va A56 uchun "
        "maksimal tezlik.\n\n"
        "USB-C kabel toʻplamda.",
    ),
    "charger-apple-20w": (
        "Оригинальный адаптер Apple 20 Вт USB-C. Подходит для всех iPhone — нужен только подходящий кабель.\n\n"
        "Кабель продаётся отдельно.",
        "Apple'ning original 20 Vt USB-C adapteri. Barcha iPhone'larga mos — faqat mos kabel kerak.\n\n"
        "Kabel alohida sotiladi.",
    ),
    "charger-baseus-65w": (
        "Зарядка Baseus GaN на 65 Вт с тремя портами: можно одновременно заряжать ноутбук, телефон и "
        "наушники.\n\n"
        "Подходит и для ноутбуков с USB-C.",
        "Uchta portli Baseus GaN 65 Vt quvvatlagichi: noutbuk, telefon va quloqchinlarni bir vaqtda "
        "quvvatlash mumkin.\n\n"
        "USB-C noutbuklar uchun ham mos.",
    ),
    "charger-ugreen-100w": (
        "Ugreen Nexode 100 Вт с четырьмя портами — одна зарядка на весь стол: ноутбук, планшет и два "
        "телефона.\n\n"
        "Технология GaN: заметно меньше обычных зарядок такой мощности.",
        "Toʻrtta portli Ugreen Nexode 100 Vt — butun stol uchun bitta quvvatlagich: noutbuk, planshet va "
        "ikkita telefon.\n\n"
        "GaN texnologiyasi: shunday quvvatli oddiy quvvatlagichlardan ancha kichik.",
    ),
    "powerbank-anker-10000": (
        "Anker Nano 10000 мА·ч со встроенным кабелем USB-C — не нужно носить отдельный провод. Мощность 30 Вт: "
        "быстро заряжает iPhone и Galaxy.\n\n"
        "Экран показывает оставшийся заряд в процентах.",
        "Ichiga USB-C kabel oʻrnatilgan Anker Nano 10000 mA·soat — alohida sim olib yurish shart emas. "
        "30 Vt quvvat: iPhone va Galaxy'ni tez quvvatlaydi.\n\n"
        "Ekran qolgan zaryadni foizda koʻrsatadi.",
    ),
    "powerbank-xiaomi-20000": (
        "Xiaomi 20000 мА·ч на 22,5 Вт — хватит на 3–4 полные зарядки телефона.\n\n"
        "Можно заряжать два устройства сразу.",
        "22,5 Vt quvvatli Xiaomi 20000 mA·soat — telefonni 3–4 marta toʻliq quvvatlashga yetadi.\n\n"
        "Ikki qurilmani bir vaqtda quvvatlash mumkin.",
    ),
    "powerbank-baseus-magnetic": (
        "Магнитный аккумулятор Baseus 10000 мА·ч крепится к iPhone с MagSafe и заряжает без проводов. "
        "Через USB-C — до 20 Вт.\n\n"
        "Удобно в дороге: телефон заряжается прямо в руке.",
        "Baseus 10000 mA·soat magnitli powerbanki MagSafe'li iPhone'ga yopishadi va simsiz quvvatlaydi. "
        "USB-C orqali — 20 Vt gacha.\n\n"
        "Yoʻlda qulay: telefon qoʻlda turib quvvatlanadi.",
    ),
}
for _device, _model, _variants in CASES:
    DESCRIPTIONS[case_slug(_device)] = (
        f"Чехол Spigen для {_model}: жёсткая спинка и мягкие бампера с воздушными подушками в углах защищают "
        "при падениях. Кнопки нажимаются легко, разъёмы и камеры открыты.\n\n"
        "Можно выбрать подарком к телефону, если позволяет бюджет подарка.",
        f"{_model} uchun Spigen gʻilofi: qattiq orqa qism va burchaklari havo yostiqchali yumshoq bamperlar "
        "tushganda himoya qiladi. Tugmalar oson bosiladi, ulagichlar va kameralar ochiq.\n\n"
        "Sovgʻa byudjeti yetsa, telefonga sovgʻa sifatida tanlash mumkin.",
    )
for _device, _model, _brand, _brand_name, _qty, _sku, _cost in GLASSES:
    _pack_ru = "два стекла" if _qty == 2 else "одно стекло"
    _pack_uz = "ikkita oyna" if _qty == 2 else "bitta oyna"
    DESCRIPTIONS[glass_slug(_device)] = (
        f"Защитное стекло {_brand_name} для {_model} с рамкой для точной поклейки — без пузырей с первого раза. "
        f"В комплекте {_pack_ru}.\n\n"
        "Совместимо с чехлами. Можно выбрать подарком к телефону.",
        f"{_model} uchun {_brand_name} himoya oynasi aniq yopishtirish ramkasi bilan — birinchi urinishda "
        f"pufakchalarsiz. Toʻplamda {_pack_uz}.\n\n"
        "Gʻiloflar bilan mos. Telefonga sovgʻa sifatida tanlash mumkin.",
    )

# Свой склад: сколько устройств с IMEI лежит на складе
OWN_STOCK = {
    "IP16P-256-BLK": 3, "IP16P-128-BLK": 2, "IP15-128-BLK": 2, "IP17PM-256-ORG": 2, "IP17P-256-ORG": 3,
    "IP17P-256-BLU": 2, "IP17-256-BLK": 3, "IP16-128-BLK": 2, "IP16E-128-BLK": 2, "S25-256-BLU": 2,
    "A56-128-BLK": 3, "A36-128-BLK": 2, "RN14-256-BLK": 4, "R14C-128-BLK": 3, "IPAD11-128-BLU": 2,
}
# Прайс этих позиций у поставщика устарел — на витрине их нет, пока поставщик не обновит цены
STALE_SUPPLIER_SKUS = {"RN14P-256-BLU", "S25U-512-TIT", "ZFOLD7-512-SLV", "XPAD7-256-GRN"}
# Samsung и Honor везёт отдельный поставщик, остальное — основной
SECOND_SUPPLIER_BRANDS = {"samsung", "honor"}
GIFTABLE = {sku for _, _, variants in CASES for sku, _, _ in variants} | {row[5] for row in GLASSES} | {
    "CHG-ANKER-30"
}
# Зарядки и аккумуляторы подходят телефонам с USB-C, если их мощности хватает для быстрой зарядки
POWER_ACCESSORIES = ["charger-anker-30w", "charger-samsung-45w", "charger-apple-20w", "charger-baseus-65w",
                     "charger-ugreen-100w", "powerbank-anker-10000", "powerbank-xiaomi-20000",
                     "powerbank-baseus-magnetic"]

# Наценки по категориям: процент, минимальная маржа в сумах, шаг округления цены
MARKUPS = {
    "cases": (Decimal("25"), 20_000, 1000),
    "chargers": (Decimal("25"), 20_000, 1000),
    "screen-protectors": (Decimal("30"), 15_000, 1000),
    "power-banks": (Decimal("20"), 30_000, 1000),
    "headphones": (Decimal("15"), 50_000, 1000),
    "smartwatches": (Decimal("12"), 80_000, 10_000),
}
