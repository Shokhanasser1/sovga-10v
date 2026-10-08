from datetime import timedelta

import pytest
from django.db import transaction
from django.utils import timezone

from apps.notifications import outbox
from apps.notifications.models import OutboxEvent
from apps.notifications.telegram import notify_managers, send_message

pytestmark = pytest.mark.django_db

NOW = timezone.now()


@pytest.fixture
def handlers(monkeypatch):
    registry = {}
    monkeypatch.setattr(outbox, "_HANDLERS", registry)
    return registry


def test_event_is_not_emitted_when_the_transaction_rolls_back():
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            outbox.emit("order.created", {"number": "1"})
            raise RuntimeError("заказ не сохранился")

    assert not OutboxEvent.objects.exists()


def test_successful_delivery(handlers):
    seen = []
    handlers["ping"] = seen.append
    event = outbox.emit("ping", {"n": 1}, now=NOW)

    result = outbox.deliver_pending(NOW)

    event.refresh_from_db()
    assert seen == [{"n": 1}]
    assert (event.status, result.done) == (OutboxEvent.Status.DONE, 1)


def test_failure_is_retried_with_backoff_then_given_up(handlers):
    def broken(payload):
        raise ConnectionError("Telegram недоступен")

    handlers["ping"] = broken
    event = outbox.emit("ping", {}, now=NOW)

    outbox.deliver_pending(NOW)
    event.refresh_from_db()
    assert (event.status, event.attempts) == (OutboxEvent.Status.PENDING, 1)
    assert event.next_attempt_at == NOW + timedelta(minutes=1)
    assert "Telegram недоступен" in event.last_error

    moment = NOW
    for _ in range(len(outbox.BACKOFF)):
        moment = event.next_attempt_at
        outbox.deliver_pending(moment)
        event.refresh_from_db()
    assert event.status == OutboxEvent.Status.FAILED
    assert event.attempts == len(outbox.BACKOFF) + 1


def test_events_not_yet_due_are_skipped(handlers):
    seen = []
    handlers["ping"] = seen.append
    outbox.emit("ping", {}, now=NOW + timedelta(minutes=5))

    assert outbox.deliver_pending(NOW).done == 0
    assert seen == []


def test_unknown_event_type_fails(handlers):
    event = outbox.emit("nobody.listens", {}, now=NOW)

    outbox.deliver_pending(NOW)

    event.refresh_from_db()
    assert event.status == OutboxEvent.Status.FAILED
    assert "обработчик" in event.last_error


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_send_message_request():
    calls = []

    def http_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({"ok": True})

    send_message(42, "Новый заказ", token="bot-token", http_post=http_post)

    url, kwargs = calls[0]
    assert url == "https://api.telegram.org/botbot-token/sendMessage"
    assert kwargs["json"]["chat_id"] == 42
    assert kwargs["json"]["text"] == "Новый заказ"


def test_send_message_error():
    with pytest.raises(Exception):
        send_message(42, "x", token="t", http_post=lambda url, **kw: FakeResponse({"ok": False, "description": "chat not found"}))


def test_notify_managers_sends_to_every_chat(settings, monkeypatch):
    settings.TELEGRAM_BOT_TOKEN = "t"
    settings.MANAGER_CHAT_IDS = ["1", "2"]
    sent = []
    monkeypatch.setattr("apps.notifications.telegram.send_message", lambda chat, text: sent.append((chat, text)))

    assert notify_managers("Новый заказ") == 2
    assert sent == [("1", "Новый заказ"), ("2", "Новый заказ")]


def test_notify_managers_without_bot_does_nothing(settings, monkeypatch):
    settings.TELEGRAM_BOT_TOKEN = ""
    monkeypatch.setattr("apps.notifications.telegram.send_message", lambda chat, text: pytest.fail("не должно быть отправки"))

    assert notify_managers("Новый заказ") == 0


def test_secrets_never_reach_the_error_log(handlers, settings):
    settings.TELEGRAM_BOT_TOKEN = "123456:SECRET-BOT-TOKEN"

    def leaky(payload):
        raise ConnectionError("Max retries exceeded with url: /bot123456:SECRET-BOT-TOKEN/sendMessage")

    handlers["ping"] = leaky
    event = outbox.emit("ping", {}, now=NOW)

    outbox.deliver_pending(NOW)

    event.refresh_from_db()
    assert "SECRET-BOT-TOKEN" not in event.last_error
    assert "***" in event.last_error


def test_telegram_network_error_does_not_expose_the_url():
    import requests

    from apps.notifications.telegram import TelegramError

    def http_post(url, **kwargs):
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}")

    with pytest.raises(TelegramError) as exc:
        send_message(1, "x", token="123456:SECRET", http_post=http_post)
    assert "SECRET" not in str(exc.value)
