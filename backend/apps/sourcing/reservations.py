"""Резервы под корзину и заказ."""

from datetime import datetime, timedelta

from django.db import transaction

from apps.catalog.models import Variant

from .models import Offer, Reservation
from .routing import available_qty, choose_offer

DEFAULT_TTL = timedelta(minutes=15)


@transaction.atomic
def reserve(
    variant: Variant, qty: int, ref: str, now: datetime, ttl: timedelta = DEFAULT_TTL
) -> Reservation | None:
    if qty < 1:
        raise ValueError("Количество — минимум 1")
    offer = choose_offer(variant, qty, now)
    if offer is None:
        return None
    locked = Offer.objects.select_for_update().get(pk=offer.pk)
    if available_qty(locked, now) < qty:
        return None
    return Reservation.objects.create(
        offer=locked, qty=qty, ref=ref, is_soft=not locked.is_own, expires_at=now + ttl
    )


def release(reservation: Reservation, now: datetime) -> None:
    if reservation.released_at is None:
        reservation.released_at = now
        reservation.save(update_fields=["released_at"])


def release_expired(now: datetime) -> int:
    return Reservation.objects.filter(released_at__isnull=True, expires_at__lte=now).update(
        released_at=now
    )
