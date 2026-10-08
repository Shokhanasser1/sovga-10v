"""Ссылки t.me/<бот>?start=<вид>_<код>: по ним бот узнаёт, чей это чат."""

import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from apps.customers.models import Customer
from apps.sourcing.models import Supplier

from .models import TelegramLink

LINK_TTL = timedelta(hours=24)
K = TelegramLink.Kind


def _deep_link(now: datetime, kind: str, **target) -> str:
    TelegramLink.objects.filter(kind=kind, used_at__isnull=True, **target).delete()
    link = TelegramLink.objects.create(
        code=secrets.token_urlsafe(16), kind=kind, created_at=now, expires_at=now + LINK_TTL, **target
    )
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={kind}_{link.code}"


def customer_link(customer: Customer, now: datetime) -> str:
    return _deep_link(now, K.CUSTOMER, customer=customer)


def supplier_link(supplier: Supplier, now: datetime) -> str:
    return _deep_link(now, K.SUPPLIER, supplier=supplier)


@transaction.atomic
def redeem(payload: str, chat_id: int, now: datetime) -> TelegramLink | None:
    """Привязывает чат по коду. Код одноразовый; один чат — один покупатель или один поставщик."""
    kind, _, code = payload.partition("_")
    link = (
        TelegramLink.objects.select_for_update()
        .filter(kind=kind, code=code, used_at__isnull=True, expires_at__gt=now)
        .first()
    )
    if link is None:
        return None
    link.used_at = now
    link.save(update_fields=["used_at"])
    model, target_id = (Customer, link.customer_id) if kind == K.CUSTOMER else (Supplier, link.supplier_id)
    model.objects.filter(telegram_chat_id=chat_id).exclude(pk=target_id).update(telegram_chat_id=None)
    model.objects.filter(pk=target_id).update(telegram_chat_id=chat_id)
    return link
