"""Outbox: надёжная доставка событий («новый заказ», «отправить в Telegram»).

emit() вызывается внутри транзакции изменения данных; deliver_pending() — из run_jobs и run_bot.
Обработчики регистрируются приложениями в AppConfig.ready() через @register.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from .models import OutboxEvent

logger = logging.getLogger(__name__)

Handler = Callable[[dict], None]
BACKOFF = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=3),
    timedelta(hours=6),
]
# Событие в работе у одного процесса; если он упал посреди отправки, через это время событие возьмёт другой.
CLAIM_LEASE = timedelta(minutes=5)
_HANDLERS: dict[str, Handler] = {}
SECRET_SETTINGS = (
    "SECRET_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_GATEWAY_TOKEN", "ESKIZ_PASSWORD", "INTERNAL_API_TOKEN",
)


def _redact(text: str) -> str:
    """Ошибки внешних сервисов могут содержать токены (например, в адресе Bot API) — вычищаем."""
    for name in SECRET_SETTINGS:
        value = getattr(settings, name, "")
        if value and len(value) >= 6:
            text = text.replace(value, "***")
    return text


@dataclass
class DeliveryResult:
    done: int = 0
    retried: int = 0
    failed: int = 0


def register(event_type: str) -> Callable[[Handler], Handler]:
    def decorator(handler: Handler) -> Handler:
        _HANDLERS[event_type] = handler
        return handler

    return decorator


def emit(event_type: str, payload: dict, now: datetime | None = None) -> OutboxEvent:
    return OutboxEvent.objects.create(type=event_type, payload=payload, next_attempt_at=now or timezone.now())


def _record_failure(event: OutboxEvent, now: datetime, error: str, result: DeliveryResult) -> None:
    event.attempts += 1
    event.last_error = error
    if event.attempts > len(BACKOFF):
        event.status = OutboxEvent.Status.FAILED
        event.processed_at = now
        result.failed += 1
        logger.error("Событие %s не доставлено после %s попыток: %s", event, event.attempts, error)
    else:
        event.next_attempt_at = now + BACKOFF[event.attempts - 1]
        result.retried += 1


def deliver_pending(now: datetime, limit: int = 100) -> DeliveryResult:
    result = DeliveryResult()
    due = OutboxEvent.objects.filter(status=OutboxEvent.Status.PENDING, next_attempt_at__lte=now).order_by("pk")
    for event in due[:limit]:
        claimed = OutboxEvent.objects.filter(
            pk=event.pk, status=OutboxEvent.Status.PENDING, next_attempt_at=event.next_attempt_at
        ).update(next_attempt_at=now + CLAIM_LEASE)
        if not claimed:  # его уже забрал другой процесс
            continue
        handler = _HANDLERS.get(event.type)
        if handler is None:
            event.status = OutboxEvent.Status.FAILED
            event.last_error = f"Нет обработчика для «{event.type}»"
            event.processed_at = now
            result.failed += 1
        else:
            try:
                handler(event.payload)
            except Exception as error:  # внешний сервис упал — запоминаем и повторим позже, очередь не останавливаем
                _record_failure(event, now, _redact(f"{type(error).__name__}: {error}"), result)
            else:
                event.status = OutboxEvent.Status.DONE
                event.processed_at = now
                result.done += 1
        event.save()
    return result
