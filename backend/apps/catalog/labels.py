"""Названия модификаций для людей: «iPhone 15 · 128 ГБ · Чёрный · nano-SIM + eSIM».

Для сопоставления прайсов поставщиков — sourcing.matching.variant_label (там нужны исходные коды).
"""

from .models import Variant

VALUE_LABELS = {
    "black": "Чёрный", "white": "Белый", "blue": "Синий", "green": "Зелёный", "titanium": "Титан",
    "grey": "Серый", "clear": "Прозрачный", "nano_esim": "nano-SIM + eSIM", "esim_only": "Только eSIM",
    "dual_sim": "2 SIM", "usb-c": "USB-C", "lightning": "Lightning",
}


def variant_title(variant: Variant) -> str:
    units = {d.code: d.unit for d in variant.product_model.category.effective_attributes()}
    parts = [variant.product_model.name_ru]
    for code, value in variant.axes.items():
        if isinstance(value, str):
            parts.append(VALUE_LABELS.get(value, value))
        else:
            parts.append(f"{value} {units.get(code, '')}".strip())
    return " · ".join(parts)
