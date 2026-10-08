"""Узбекские мобильные номера: приводим любую запись к +998XXXXXXXXX."""

import re


def normalize_uz_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return None
