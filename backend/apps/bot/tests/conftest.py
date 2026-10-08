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


class FakeTelegram:
    """Bot API без сети: getUpdates отдаёт подготовленные обновления, sendMessage — номер сообщения."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.updates: list[dict] = []

    def __call__(self, method, payload, **kwargs):
        self.calls.append((method, payload))
        if method == "getUpdates":
            updates, self.updates = self.updates, []
            return updates
        if method == "sendMessage":
            return {"message_id": len(self.calls)}
        return True

    def sent(self, chat_id=None) -> list[str]:
        return [
            payload["text"] for method, payload in self.calls
            if method == "sendMessage" and (chat_id is None or payload["chat_id"] == chat_id)
        ]

    def last(self, method: str) -> dict:
        return [payload for name, payload in self.calls if name == method][-1]


@pytest.fixture
def telegram(monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr("apps.notifications.telegram.call", fake)
    return fake


@pytest.fixture
def customer(db):
    return customer_for_phone("+998901112233")


def start_payload(url: str) -> str:
    return url.split("?start=", 1)[1]


def message(chat_id: int, text: str, update_id: int = 1) -> dict:
    return {"update_id": update_id, "message": {"message_id": 10, "chat": {"id": chat_id, "type": "private"}, "text": text}}
