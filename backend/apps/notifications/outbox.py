"""Outbox: надёжная доставка событий («новый заказ», «отправить в Telegram»).

emit() вызывается внутри транзакции изменения данных; deliver_pending() — из run_jobs.
Обработчики регистрируются приложениями в AppConfig.ready() через @register.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

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
_HANDLERS: dict[str, Handler] = {}


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
                _record_failure(event, now, f"{type(error).__name__}: {error}", result)
            else:
                event.status = OutboxEvent.Status.DONE
                event.processed_at = now
                result.done += 1
        event.save()
    return result
