"""Узбекские мобильные номера: приводим любую запись к +998XXXXXXXXX."""

import re


def normalize_uz_phone(raw: str) -> str | None:
    # Только ASCII-цифры: \d в Python понимает и «٩», и «９» — один номер получил бы разные записи
    # и обходил бы лимиты на номер.
    digits = re.sub(r"[^0-9]", "", raw)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return None
