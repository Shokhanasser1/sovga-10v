from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.pricing.cbu import CBU_URL, fetch_usd_rate, parse_usd_rate
from apps.pricing.models import ExchangeRate

SAMPLE = [
    {
        "id": 69, "Code": "840", "Ccy": "USD", "CcyNm_RU": "Доллар США", "Nominal": "1",
        "Rate": "12850.55", "Diff": "-10.01", "Date": "07.10.2026",
    }
]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self.payload


def test_parse_usd_rate():
    assert parse_usd_rate(SAMPLE) == (date(2026, 10, 7), Decimal("12850.55"))


def test_parse_divides_by_nominal():
    payload = [dict(SAMPLE[0], Nominal="10", Rate="128505.50")]

    assert parse_usd_rate(payload) == (date(2026, 10, 7), Decimal("12850.55"))


def test_parse_without_usd_fails():
    with pytest.raises(ValueError):
        parse_usd_rate([dict(SAMPLE[0], Ccy="EUR")])


def test_fetch_requests_dated_url():
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse(SAMPLE)

    result = fetch_usd_rate(date(2026, 10, 7), http_get=fake_get)

    assert result == (date(2026, 10, 7), Decimal("12850.55"))
    assert calls == [(CBU_URL.format(day="2026-10-07"), 10)]


def test_fetch_raises_on_http_error():
    with pytest.raises(RuntimeError):
        fetch_usd_rate(date(2026, 10, 7), http_get=lambda url, timeout: FakeResponse([], status=503))


@pytest.mark.django_db
def test_command_upserts_rate_and_keeps_spread(monkeypatch):
    ExchangeRate.objects.create(date=date(2026, 10, 7), cbu_rate=Decimal("1"), spread_pct=Decimal("2"))
    monkeypatch.setattr(
        "apps.pricing.management.commands.fetch_cbu_rate.fetch_usd_rate",
        lambda day: (date(2026, 10, 7), Decimal("12850.55")),
    )

    call_command("fetch_cbu_rate")

    rate = ExchangeRate.objects.get(date=date(2026, 10, 7))
    assert rate.cbu_rate == Decimal("12850.55")
    assert rate.spread_pct == Decimal("2")
