"""Курс USD Центрального банка Узбекистана (cbu.uz)."""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import requests

CBU_URL = "https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/{day}/"


def parse_usd_rate(payload: object) -> tuple[date, Decimal]:
    if not isinstance(payload, list):
        raise ValueError("Неожиданный ответ ЦБ")
    for item in payload:
        if isinstance(item, dict) and item.get("Ccy") == "USD":
            rate = Decimal(item["Rate"]) / Decimal(item.get("Nominal") or "1")
            day = datetime.strptime(item["Date"], "%d.%m.%Y").date()
            return day, rate.quantize(Decimal("0.01"))
    raise ValueError("В ответе ЦБ нет курса USD")


def fetch_usd_rate(
    day: date, http_get: Callable[..., requests.Response] = requests.get
) -> tuple[date, Decimal]:
    response = http_get(CBU_URL.format(day=day.isoformat()), timeout=10)
    response.raise_for_status()
    return parse_usd_rate(response.json())
