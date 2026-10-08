"""Ссылки, по которым покупатель уходит платить. Только настройки — без обращений к базе."""

import base64
from urllib.parse import urlencode

from django.conf import settings

from apps.orders.models import Order


class PaymentUnavailable(Exception):
    pass


def _return_url(order: Order, lang: str) -> str:
    return f"{settings.SITE_URL.rstrip('/')}/{lang}/orders/{order.number}"


def payme_configured() -> bool:
    return bool(settings.PAYME_MERCHANT_ID and settings.PAYME_KEY)


def click_configured() -> bool:
    return bool(settings.CLICK_SERVICE_ID and settings.CLICK_MERCHANT_ID and settings.CLICK_SECRET_KEY)


def simulated(provider: str) -> bool:
    """Учебный режим: провайдер без ключей имитируется. Настоящие ключи главнее имитации."""
    ready = {"payme": payme_configured, "click": click_configured}.get(provider)
    return bool(settings.DEMO_MODE and ready and not ready())


def configured_providers() -> list[str]:
    return [
        name for name, ready in (("payme", payme_configured()), ("click", click_configured()))
        if ready or simulated(name)
    ]


def payme_url(order: Order, lang: str) -> str:
    if not payme_configured():
        raise PaymentUnavailable
    params = (
        f"m={settings.PAYME_MERCHANT_ID};ac.{settings.PAYME_ACCOUNT_FIELD}={order.number};"
        f"a={order.total_uzs * 100};c={_return_url(order, lang)};l={lang}"
    )
    return f"{settings.PAYME_CHECKOUT_URL.rstrip('/')}/{base64.b64encode(params.encode()).decode()}"


def click_url(order: Order, lang: str) -> str:
    if not click_configured():
        raise PaymentUnavailable
    query = urlencode(
        {
            "service_id": settings.CLICK_SERVICE_ID,
            "merchant_id": settings.CLICK_MERCHANT_ID,
            "amount": order.total_uzs,
            "transaction_param": order.number,
            "return_url": _return_url(order, lang),
        }
    )
    return f"{settings.CLICK_PAY_URL}?{query}"


LINKS = {"payme": payme_url, "click": click_url}
