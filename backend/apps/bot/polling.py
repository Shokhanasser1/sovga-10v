"""Long polling: забираем обновления у Telegram и обрабатываем по одному."""

import logging

from django.utils import timezone

from apps.notifications import telegram

from . import texts
from .dispatch import handle_update

logger = logging.getLogger(__name__)
POLL_SECONDS = 25


def _chat_of(update: dict) -> int | None:
    message = update.get("message") or (update.get("callback_query") or {}).get("message") or {}
    return (message.get("chat") or {}).get("id")


def _apologize(update: dict) -> None:
    chat_id = _chat_of(update)
    if chat_id is None:
        return
    try:
        telegram.send_message(chat_id, texts.FAILED)
    except telegram.TelegramError:
        pass


def poll_once(offset: int | None) -> int | None:
    """Один запрос getUpdates. Возвращает смещение: Telegram больше не пришлёт то, что уже обработано."""
    payload: dict = {"timeout": POLL_SECONDS, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    for update in telegram.call("getUpdates", payload, timeout=POLL_SECONDS + 10):
        offset = update["update_id"] + 1
        try:
            handle_update(update, timezone.now())
        except Exception:  # одно сломанное обновление не должно останавливать бота
            logger.exception("Обновление Telegram %s не обработано", update.get("update_id"))
            _apologize(update)
    return offset
