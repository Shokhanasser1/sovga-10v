"""Отправка сообщений через Telegram Bot API."""

import logging
from collections.abc import Callable

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


def send_message(
    chat_id: int | str,
    text: str,
    token: str | None = None,
    http_post: Callable[..., requests.Response] = requests.post,
) -> None:
    token = token or settings.TELEGRAM_BOT_TOKEN
    response = http_post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=10,
    )
    payload = response.json()
    if not payload.get("ok"):
        raise TelegramError(payload.get("description", "Telegram отклонил сообщение"))


def notify_managers(text: str) -> int:
    """Сообщение всем менеджерам. Бот не настроен — ничего не отправляем, только пишем в лог."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.MANAGER_CHAT_IDS:
        logger.warning("Уведомление менеджерам не отправлено — бот не настроен: %s", text)
        return 0
    for chat_id in settings.MANAGER_CHAT_IDS:
        send_message(chat_id, text)
    return len(settings.MANAGER_CHAT_IDS)
