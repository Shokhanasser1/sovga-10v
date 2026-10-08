"""Коды входа: выдача с ограничениями и проверка.

Ограничения: код живёт 5 минут; действует только последний выданный; повтор — не раньше чем через
минуту; не больше 5 кодов в час и 10 в сутки на номер; не больше 5 попыток ввода на код.
Итого не больше 50 попыток угадать код в сутки на номер — при миллионе вариантов это 0,005 %.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F

from .models import OtpCode, OtpPhone
from .senders import DeliveryError, OtpSender

CODE_TTL = timedelta(minutes=5)
RESEND_AFTER = timedelta(seconds=60)
MAX_PER_HOUR = 5
MAX_PER_DAY = 10
MAX_ATTEMPTS = 5


class OtpError(Exception):
    """Сообщение безопасно показывать покупателю; code — для фронтенда."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


def _hash(phone: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def _new_code() -> str:
    if settings.DEBUG and settings.OTP_FIXED_CODE:
        return settings.OTP_FIXED_CODE
    return f"{secrets.randbelow(1_000_000):06d}"


def _active(phone: str, now: datetime):
    return OtpCode.objects.filter(phone=phone, consumed_at__isnull=True, expires_at__gt=now)


def _check_limits(phone: str, now: datetime) -> None:
    day = OtpCode.objects.filter(phone=phone, created_at__gte=now - timedelta(days=1))
    last = day.first()
    if last and now - last.created_at < RESEND_AFTER:
        raise OtpError("Код уже отправлен. Запросить новый можно через минуту.", "too_soon")
    if day.filter(created_at__gte=now - timedelta(hours=1)).count() >= MAX_PER_HOUR or day.count() >= MAX_PER_DAY:
        raise OtpError("Слишком много кодов. Попробуйте позже.", "too_many")


def _lock_phone(phone: str, now: datetime) -> None:
    """UPDATE держит блокировку строки номера до конца транзакции — и в PostgreSQL, и в SQLite."""
    OtpPhone.objects.bulk_create([OtpPhone(phone=phone)], ignore_conflicts=True)
    OtpPhone.objects.filter(phone=phone).update(locked_at=now)


@transaction.atomic
def _issue(phone: str, now: datetime, ip: str | None) -> tuple[OtpCode, str]:
    _lock_phone(phone, now)
    _check_limits(phone, now)
    _active(phone, now).update(expires_at=now)  # действует только последний код
    code = _new_code()
    otp = OtpCode.objects.create(
        phone=phone, code_hash=_hash(phone, code), created_at=now, expires_at=now + CODE_TTL, ip=ip
    )
    return otp, code


def request_code(phone: str, now: datetime, sender: OtpSender, ip: str | None = None) -> OtpCode:
    otp, code = _issue(phone, now, ip)
    # Отправляем уже после транзакции: сетевой запрос не держит блокировку номера.
    try:
        otp.channel = sender.send(phone, code)
    except DeliveryError as error:
        OtpCode.objects.filter(pk=otp.pk).update(expires_at=now)  # код никто не получил — угадывать нечего
        raise OtpError("Не удалось отправить код. Попробуйте позже.", "delivery_failed") from error
    otp.save(update_fields=["channel"])
    return otp


def verify_code(phone: str, code: str, now: datetime) -> None:
    # Ошибку поднимаем после транзакции: иначе откат отменил бы счётчик попыток.
    error = _check_and_count_attempt(phone, code, now)
    if error:
        raise error


@transaction.atomic
def _check_and_count_attempt(phone: str, code: str, now: datetime) -> OtpError | None:
    otp = _active(phone, now).select_for_update().first()
    if otp is None:
        return OtpError("Код истёк или уже использован. Запросите новый.", "expired")
    # Условное увеличение в одном UPDATE: параллельные запросы не проскочат лимит даже без блокировок.
    counted = OtpCode.objects.filter(pk=otp.pk, attempts__lt=MAX_ATTEMPTS).update(attempts=F("attempts") + 1)
    if not counted:
        return OtpError("Слишком много неверных попыток. Запросите новый код.", "locked")
    if not hmac.compare_digest(otp.code_hash, _hash(phone, code.strip())):
        return OtpError("Неверный код.", "wrong")
    used = OtpCode.objects.filter(pk=otp.pk, consumed_at__isnull=True).update(consumed_at=now)
    if not used:
        return OtpError("Код истёк или уже использован. Запросите новый.", "expired")
    return None
