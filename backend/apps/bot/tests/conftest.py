"""Бот с фальшивым Telegram: все вызовы Bot API складываются в список."""

import pytest
from django.utils import timezone

from apps.customers.services import customer_for_phone
from apps.orders.tests.conftest import shop  # noqa: F401 — фикстура магазина

NOW = timezone.now()


@pytest.fixture
def bot(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:test"
    settings.TELEGRAM_BOT_USERNAME = "sovga_test_bot"
    settings.MANAGER_CHAT_IDS = ["-100"]


@pytest.fixture
def telegram(monkeypatch):
    """Подменяет Bot API: вызовы записываются, sendMessage отвечает номером сообщения."""
    calls: list[tuple[str, dict]] = []

    def call(method, payload, **kwargs):
        calls.append((method, payload))
        return {"message_id": len(calls)} if method == "sendMessage" else True

    monkeypatch.setattr("apps.notifications.telegram.call", call)
    return calls


def sent(calls, chat_id=None) -> list[str]:
    return [p["text"] for m, p in calls if m == "sendMessage" and (chat_id is None or p["chat_id"] == chat_id)]


@pytest.fixture
def customer(db):
    return customer_for_phone("+998901112233")


def start_payload(url: str) -> str:
    return url.split("?start=", 1)[1]
