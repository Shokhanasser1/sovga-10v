from datetime import timedelta

import pytest
from django.utils import timezone

from apps.customers.otp import OtpError, request_code, verify_code
from apps.customers.phones import normalize_uz_phone
from apps.customers.senders import DeliveryError
from apps.customers.services import customer_for_phone

PHONE = "+998901234567"


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, phone, code):
        self.sent.append((phone, code))
        return "fake"


class BrokenSender:
    def send(self, phone, code):
        raise DeliveryError("сеть недоступна")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+998 90 123-45-67", PHONE),
        ("998901234567", PHONE),
        ("90 123 45 67", PHONE),
        ("(90) 1234567", PHONE),
        ("+7 900 123 45 67", None),
        ("12345", None),
        ("", None),
    ],
)
def test_normalize_uz_phone(raw, expected):
    assert normalize_uz_phone(raw) == expected


@pytest.mark.django_db
def test_code_is_sent_and_verified_once():
    sender, now = FakeSender(), timezone.now()
    otp = request_code(PHONE, now, sender, ip="8.8.8.8")
    [(phone, code)] = sender.sent

    assert phone == PHONE and len(code) == 6 and code.isdigit()
    assert otp.channel == "fake"
    assert code not in otp.code_hash
    verify_code(PHONE, code, now + timedelta(minutes=1))
    with pytest.raises(OtpError) as exc:
        verify_code(PHONE, code, now + timedelta(minutes=2))
    assert exc.value.code == "expired"


@pytest.mark.django_db
def test_resend_only_after_a_minute():
    sender, now = FakeSender(), timezone.now()
    request_code(PHONE, now, sender)

    with pytest.raises(OtpError) as exc:
        request_code(PHONE, now + timedelta(seconds=30), sender)
    assert exc.value.code == "too_soon"
    request_code(PHONE, now + timedelta(seconds=61), sender)
    assert len(sender.sent) == 2


@pytest.mark.django_db
def test_at_most_five_codes_per_hour():
    sender, now = FakeSender(), timezone.now()
    for step in range(5):
        request_code(PHONE, now + timedelta(minutes=step * 2), sender)

    with pytest.raises(OtpError) as exc:
        request_code(PHONE, now + timedelta(minutes=12), sender)
    assert exc.value.code == "too_many"


@pytest.mark.django_db
def test_code_expires_after_five_minutes():
    sender, now = FakeSender(), timezone.now()
    request_code(PHONE, now, sender)

    with pytest.raises(OtpError) as exc:
        verify_code(PHONE, sender.sent[0][1], now + timedelta(minutes=6))
    assert exc.value.code == "expired"


@pytest.mark.django_db
def test_five_wrong_attempts_lock_the_code():
    sender, now = FakeSender(), timezone.now()
    request_code(PHONE, now, sender)
    right = sender.sent[0][1]
    wrong = "000000" if right != "000000" else "111111"

    for _ in range(5):
        with pytest.raises(OtpError) as exc:
            verify_code(PHONE, wrong, now)
        assert exc.value.code == "wrong"
    with pytest.raises(OtpError) as exc:
        verify_code(PHONE, right, now)
    assert exc.value.code == "locked"


@pytest.mark.django_db
def test_delivery_failure_is_reported():
    with pytest.raises(OtpError) as exc:
        request_code(PHONE, timezone.now(), BrokenSender())

    assert exc.value.code == "delivery_failed"


@pytest.mark.django_db
def test_fixed_code_only_in_debug(settings):
    settings.DEBUG = True
    settings.OTP_FIXED_CODE = "424242"
    sender = FakeSender()

    request_code(PHONE, timezone.now(), sender)

    assert sender.sent[0][1] == "424242"


@pytest.mark.django_db
def test_fixed_code_is_ignored_without_debug(settings, monkeypatch):
    settings.DEBUG = False
    settings.OTP_FIXED_CODE = "424242"
    monkeypatch.setattr("apps.customers.otp.secrets.randbelow", lambda limit: 7)
    sender = FakeSender()

    request_code(PHONE, timezone.now(), sender)

    assert sender.sent[0][1] == "000007"


@pytest.mark.django_db
def test_customer_is_created_once_per_phone():
    first = customer_for_phone(PHONE)
    again = customer_for_phone(PHONE)

    assert first == again
    assert first.user.username == f"customer_{PHONE}"
    assert not first.user.has_usable_password()
