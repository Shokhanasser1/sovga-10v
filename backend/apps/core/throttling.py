"""Ограничение частоты запросов к публичному API по посетителю.

Схема доверия (при сомнении — ограничиваем, а не пропускаем):
- серверная отрисовка витрины присылает секретный X-Internal-Token — её не ограничиваем;
- от доверенного прокси (nginx на этом сервере) берём адрес из X-Real-IP: nginx
  перезаписывает этот заголовок (`proxy_set_header X-Real-IP $remote_addr`), подделать нельзя;
- X-Forwarded-For не используем: Next.js пробрасывает его от клиента как есть;
- всё остальное считаем по адресу отправителя. Запросы с 127.0.0.1 без заголовков
  попадают в общий счётчик — это безопасно, хоть и строго.
"""

import hmac

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


def is_internal(request) -> bool:
    expected = settings.INTERNAL_API_TOKEN
    given = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


def client_ident(request) -> str | None:
    if is_internal(request):
        return None
    remote = request.META.get("REMOTE_ADDR", "")
    if remote in settings.TRUSTED_PROXIES:
        real_ip = request.META.get("HTTP_X_REAL_IP", "").strip()
        if real_ip:
            return real_ip
    return remote


class ClientRateThrottle(SimpleRateThrottle):
    scope = "anon"

    def get_cache_key(self, request, view):
        ident = client_ident(request)
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class SearchRateThrottle(ClientRateThrottle):
    """Автокомплит дёргается на каждый набранный символ — отдельный, более строгий лимит."""

    scope = "search"


class OtpRateThrottle(ClientRateThrottle):
    """Запрос и проверка кода входа: защита от рассылки SMS по чужим номерам и перебора."""

    scope = "otp"
