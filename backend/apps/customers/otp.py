"""Коды входа: выдача с ограничениями и проверка."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from .models import OtpCode
from .senders import DeliveryError, OtpSender

CODE_TTL = timedelta(minutes=5)
RESEND_AFTER = timedelta(seconds=60)
MAX_PER_HOUR = 5
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


def request_code(phone: str, now: datetime, sender: OtpSender, ip: str | None = None) -> OtpCode:
    recent = OtpCode.objects.filter(phone=phone, created_at__gte=now - timedelta(hours=1))
    last = recent.first()
    if last and now - last.created_at < RESEND_AFTER:
        raise OtpError("Код уже отправлен. Запросить новый можно через минуту.", "too_soon")
    if recent.count() >= MAX_PER_HOUR:
        raise OtpError("Слишком много кодов. Попробуйте через час.", "too_many")
    code = _new_code()
    otp = OtpCode.objects.create(
        phone=phone, code_hash=_hash(phone, code), created_at=now, expires_at=now + CODE_TTL, ip=ip
    )
    try:
        otp.channel = sender.send(phone, code)
    except DeliveryError as error:
        raise OtpError("Не удалось отправить код. Попробуйте позже.", "delivery_failed") from error
    otp.save(update_fields=["channel"])
    return otp


def verify_code(phone: str, code: str, now: datetime) -> None:
    # Ошибку поднимаем после транзакции: иначе откат отменил бы счётчик попыток
    # и код можно было бы перебирать без ограничений.
    error = _check_and_count_attempt(phone, code, now)
    if error:
        raise error


@transaction.atomic
def _check_and_count_attempt(phone: str, code: str, now: datetime) -> OtpError | None:
    otp = (
        OtpCode.objects.select_for_update()
        .filter(phone=phone, consumed_at__isnull=True, expires_at__gt=now)
        .first()
    )
    if otp is None:
        return OtpError("Код истёк или уже использован. Запросите новый.", "expired")
    if otp.attempts >= MAX_ATTEMPTS:
        return OtpError("Слишком много неверных попыток. Запросите новый код.", "locked")
    otp.attempts += 1
    if not hmac.compare_digest(otp.code_hash, _hash(phone, code.strip())):
        otp.save(update_fields=["attempts"])
        return OtpError("Неверный код.", "wrong")
    otp.consumed_at = now
    otp.save(update_fields=["attempts", "consumed_at"])
    return None
