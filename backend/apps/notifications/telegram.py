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


def download_file(
    file_id: str,
    max_bytes: int,
    token: str | None = None,
    http_get: Callable[..., requests.Response] = requests.get,
) -> bytes:
    """Файл, присланный боту. Больше max_bytes — не скачиваем."""
    token = token or settings.TELEGRAM_BOT_TOKEN
    info = call("getFile", {"file_id": file_id})
    path = info.get("file_path") if isinstance(info, dict) else None
    if not path:
        raise TelegramError("Telegram не отдал файл")
    if (info.get("file_size") or 0) > max_bytes:
        raise TelegramError("Файл больше допустимого размера")
    try:
        response = http_get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=30)
        response.raise_for_status()
    except requests.RequestException as error:
        raise TelegramError(f"Telegram недоступен: {type(error).__name__}") from None  # в адресе — токен
    if len(response.content) > max_bytes:
        raise TelegramError("Файл больше допустимого размера")
    return response.content


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
