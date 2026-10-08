"""Отправка сообщений через Telegram Bot API."""

import logging
from collections.abc import Callable
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


def bot_available() -> bool:
    """Бот настроен целиком: токен для API и имя для ссылок t.me/<имя>."""
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME)


def call(
    method: str,
    payload: dict,
    token: str | None = None,
    http_post: Callable[..., requests.Response] = requests.post,
    timeout: int = 10,
) -> Any:
    token = token or settings.TELEGRAM_BOT_TOKEN
    try:
        response = http_post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=timeout)
        body = response.json()
    except (requests.RequestException, ValueError) as error:
        # Текст ошибки requests содержит адрес, а в адресе — токен бота. Наружу — только тип ошибки.
        raise TelegramError(f"Telegram недоступен: {type(error).__name__}") from None
    if not body.get("ok"):
        raise TelegramError(body.get("description", "Telegram отклонил запрос"))
    return body.get("result")


def send_message(
    chat_id: int | str,
    text: str,
    token: str | None = None,
    http_post: Callable[..., requests.Response] = requests.post,
    reply_markup: dict | None = None,
) -> int | None:
    """Простой текст без разметки: названия товаров и ввод пользователей не ломают сообщение."""
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = call("sendMessage", payload, token=token, http_post=http_post)
    return result.get("message_id") if isinstance(result, dict) else None


def notify_managers(text: str) -> int:
    """Сообщение всем менеджерам. Бот не настроен — ничего не отправляем, только пишем в лог."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.MANAGER_CHAT_IDS:
        logger.warning("Уведомление менеджерам не отправлено — бот не настроен: %s", text)
        return 0
    for chat_id in settings.MANAGER_CHAT_IDS:
        send_message(chat_id, text)
    return len(settings.MANAGER_CHAT_IDS)
