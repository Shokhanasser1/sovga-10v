from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

import pytest
import requests
from django.core.management import call_command
from django.utils import timezone

from apps.pricing.models import ExchangeRate, MarkupRule, PriceSnapshot
from apps.sourcing.models import Offer, Reservation

pytestmark = pytest.mark.django_db

FETCH = "apps.pricing.management.commands.fetch_cbu_rate.fetch_usd_rate"


def test_run_jobs_updates_rate_prices_and_reservations(monkeypatch, variant, warehouse):
    monkeypatch.setattr(FETCH, lambda day: (date(2026, 10, 8), Decimal("12800")))
    MarkupRule.objects.create(markup_pct=Decimal("10"))
    offer = Offer.objects.create(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"),
                                 qty_available=1, last_confirmed_at=timezone.now())
    Reservation.objects.create(offer=offer, qty=1, ref="cart", is_soft=False,
                               expires_at=timezone.now() - timedelta(minutes=1))

    call_command("run_jobs", stdout=StringIO(), stderr=StringIO())

    assert ExchangeRate.objects.filter(date=date(2026, 10, 8)).exists()
    assert PriceSnapshot.objects.get(variant=variant).price_uzs > 0
    assert Reservation.objects.get().released_at is not None


def test_run_jobs_survives_cbu_outage_without_rate(monkeypatch):
    def outage(day):
        raise requests.ConnectionError("cbu.uz недоступен")

    monkeypatch.setattr(FETCH, outage)
    errors = StringIO()

    call_command("run_jobs", stdout=StringIO(), stderr=errors)

    assert "Курс ЦБ не обновлён" in errors.getvalue()
    assert "Нет ни одного курса" in errors.getvalue()
