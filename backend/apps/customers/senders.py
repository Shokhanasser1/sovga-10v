"""Доставка кода входа: Telegram Gateway (дешевле), запасной канал — SMS через Eskiz.

Форматы запросов взяты из документации сервисов; перед запуском проверить в их песочницах.
"""

import logging
from collections.abc import Callable, Sequence
from typing import Protocol

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class DeliveryError(Exception):
    pass


class OtpSender(Protocol):
    def send(self, phone: str, code: str) -> str:
        """Отправить код; вернуть название канала. При неудаче — DeliveryError."""


class TelegramGatewaySender:
    URL = "https://gatewayapi.telegram.org/sendVerificationMessage"

    def __init__(self, token: str, http_post: Callable[..., requests.Response] = requests.post):
        self.token = token
        self.http_post = http_post

    def send(self, phone: str, code: str) -> str:
        try:
            response = self.http_post(
                self.URL,
                headers={"Authorization": f"Bearer {self.token}"},
                json={"phone_number": phone, "code": code, "ttl": 300},
                timeout=10,
            )
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise DeliveryError(f"Telegram Gateway недоступен: {error}") from error
        if not payload.get("ok"):
            raise DeliveryError(f"Telegram Gateway отказал: {payload.get('error')}")
        return "telegram"


class EskizSmsSender:
    BASE = "https://notify.eskiz.uz/api"

    def __init__(
        self,
        email: str,
        password: str,
        sender_name: str = "4546",
        template: str = "Sovga: kirish kodi {code}",
        http_post: Callable[..., requests.Response] = requests.post,
    ):
        self.email = email
        self.password = password
        self.sender_name = sender_name
        self.template = template
        self.http_post = http_post
        self._token: str | None = None

    def _login(self) -> str:
        if self._token is None:
            response = self.http_post(
                f"{self.BASE}/auth/login", data={"email": self.email, "password": self.password}, timeout=10
            )
            try:
                self._token = response.json()["data"]["token"]
            except (ValueError, KeyError, TypeError) as error:
                raise DeliveryError("Eskiz: не удалось войти") from error
        return self._token

    def send(self, phone: str, code: str) -> str:
        try:
            token = self._login()
            response = self.http_post(
                f"{self.BASE}/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "mobile_phone": phone.lstrip("+"),
                    "message": self.template.format(code=code),
                    "from": self.sender_name,
                },
                timeout=10,
            )
        except requests.RequestException as error:
            raise DeliveryError(f"Eskiz недоступен: {error}") from error
        if response.status_code != 200:
            raise DeliveryError(f"Eskiz отказал: HTTP {response.status_code}")
        return "sms"


class FallbackSender:
    def __init__(self, senders: Sequence[OtpSender]):
        self.senders = list(senders)

    def send(self, phone: str, code: str) -> str:
        errors = []
        for sender in self.senders:
            try:
                return sender.send(phone, code)
            except DeliveryError as error:
                errors.append(str(error))
                logger.warning("Канал %s не доставил код: %s", type(sender).__name__, error)
        raise DeliveryError("; ".join(errors) or "нет каналов доставки")


class ConsoleSender:
    """Только для разработки: код пишется в лог сервера."""

    def send(self, phone: str, code: str) -> str:
        logger.warning("Код входа для %s: %s (DEBUG, без отправки)", phone, code)
        return "console"


def build_sender() -> OtpSender:
    senders: list[OtpSender] = []
    if settings.TELEGRAM_GATEWAY_TOKEN:
        senders.append(TelegramGatewaySender(settings.TELEGRAM_GATEWAY_TOKEN))
    if settings.ESKIZ_EMAIL and settings.ESKIZ_PASSWORD:
        senders.append(
            EskizSmsSender(
                settings.ESKIZ_EMAIL, settings.ESKIZ_PASSWORD, settings.ESKIZ_FROM, settings.OTP_SMS_TEMPLATE
            )
        )
    if senders:
        return FallbackSender(senders)
    if settings.DEBUG:
        return ConsoleSender()
    raise ImproperlyConfigured(
        "Не настроена отправка кодов: задайте TELEGRAM_GATEWAY_TOKEN или ESKIZ_EMAIL и ESKIZ_PASSWORD"
    )
