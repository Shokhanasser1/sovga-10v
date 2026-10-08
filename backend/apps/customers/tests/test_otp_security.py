"""Защита входа по коду: чужие аккаунты, перебор, недоставленные и старые коды."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.customers.models import OtpCode
from apps.customers.otp import MAX_ATTEMPTS, OtpError, request_code, verify_code
from apps.customers.senders import DeliveryError
from apps.customers.services import AccountConflict, customer_for_phone

pytestmark = pytest.mark.django_db

PHONE = "+998901234567"
NOW = timezone.now()


class FakeSender:
    def __init__(self):
        self.codes = []

    def send(self, phone, code):
        self.codes.append(code)
        return "fake"


class BrokenSender:
    def send(self, phone, code):
        raise DeliveryError("нет связи")


def test_staff_account_with_the_same_login_is_never_taken_over():
    staff = get_user_model().objects.create_user(username=PHONE, password="admin-secret", is_staff=True)

    customer = customer_for_phone(PHONE)

    staff.refresh_from_db()
    assert customer.user != staff
    assert staff.check_password("admin-secret")
    assert staff.is_staff


def test_customer_users_get_their_own_login_namespace():
    customer = customer_for_phone(PHONE)

    assert customer.user.username == f"customer_{PHONE}"
    assert not customer.user.is_staff and not customer.user.is_superuser


def test_promoted_customer_login_is_not_reused():
    get_user_model().objects.create_user(username=f"customer_{PHONE}", password="x", is_staff=True)

    with pytest.raises(AccountConflict):
        customer_for_phone(PHONE)


def test_attempt_limit_holds_even_if_the_counter_was_read_stale():
    sender = FakeSender()
    request_code(PHONE, NOW, sender)
    OtpCode.objects.update(attempts=MAX_ATTEMPTS)

    with pytest.raises(OtpError) as exc:
        verify_code(PHONE, sender.codes[0], NOW)

    assert exc.value.code == "locked"


def test_at_most_ten_codes_per_day():
    sender = FakeSender()
    for step in range(10):
        request_code(PHONE, NOW + timedelta(minutes=13 * step), sender)

    with pytest.raises(OtpError) as exc:
        request_code(PHONE, NOW + timedelta(hours=3), sender)
    assert exc.value.code == "too_many"


def test_undelivered_code_cannot_be_used(monkeypatch):
    monkeypatch.setattr("apps.customers.otp.secrets.randbelow", lambda limit: 123456)
    with pytest.raises(OtpError):
        request_code(PHONE, NOW, BrokenSender())

    with pytest.raises(OtpError) as exc:
        verify_code(PHONE, "123456", NOW)
    assert exc.value.code == "expired"


def test_new_code_cancels_the_previous_one():
    sender = FakeSender()
    request_code(PHONE, NOW, sender)
    request_code(PHONE, NOW + timedelta(seconds=61), sender)
    old, new = sender.codes

    if old != new:
        with pytest.raises(OtpError):
            verify_code(PHONE, old, NOW + timedelta(seconds=62))
    verify_code(PHONE, new, NOW + timedelta(seconds=62))


def test_existing_customer_promoted_to_staff_cannot_log_in_by_code():
    customer = customer_for_phone(PHONE)
    customer.user.is_staff = True
    customer.user.save()

    with pytest.raises(AccountConflict):
        customer_for_phone(PHONE)


@pytest.mark.parametrize("raw", ["+998٩٠١٢٣٤٥٦٧", "９０ 123 45 67"])
def test_non_ascii_digits_are_rejected(raw):
    from apps.customers.phones import normalize_uz_phone

    assert normalize_uz_phone(raw) is None


def test_limits_are_checked_under_a_per_phone_lock(monkeypatch):
    """Проверка лимитов и запись кода идут под блокировкой строки номера."""
    from apps.customers import otp as otp_module
    from apps.customers.models import OtpPhone

    calls = []
    original = otp_module._check_limits

    def spy(phone, now):
        calls.append(OtpPhone.objects.filter(phone=phone).exists())
        return original(phone, now)

    monkeypatch.setattr(otp_module, "_check_limits", spy)
    request_code(PHONE, NOW, FakeSender())

    assert calls == [True]
