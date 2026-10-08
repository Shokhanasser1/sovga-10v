"""Ограничение частоты запросов к публичному API по посетителю.

Браузер ходит в API через Next.js (а в проде ещё и через nginx). Next.js пробрасывает
X-Forwarded-For как есть, nginx дописывает в конец настоящий адрес клиента. Поэтому:
- запрос от доверенного прокси с X-Forwarded-For — считаем по последнему адресу цепочки;
- от доверенного прокси без заголовка — это серверная отрисовка витрины, не ограничиваем;
- напрямую из интернета — по адресу отправителя, заголовок не учитываем.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


def client_ident(request) -> str | None:
    remote = request.META.get("REMOTE_ADDR", "")
    if remote not in settings.TRUSTED_PROXIES:
        return remote
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded:
        return None
    return forwarded.split(",")[-1].strip() or None


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
