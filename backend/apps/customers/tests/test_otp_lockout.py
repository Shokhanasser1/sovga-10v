"""Злоумышленник не может заблокировать вход владельцу номера."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.customers.otp import MAX_PER_PHONE_PER_DAY, OtpError, request_code, verify_code

pytestmark = pytest.mark.django_db

PHONE = "+998901234567"
NOW = timezone.now()
OWNER_IP = "84.54.1.1"
ATTACKER_IP = "6.6.6.6"


class FakeSender:
    def __init__(self):
        self.codes = []

    def send(self, phone, code):
        self.codes.append(code)
        return "fake"


def test_attacker_requests_do_not_cancel_the_owner_code():
    sender = FakeSender()
    owner = request_code(PHONE, NOW, sender, ip=OWNER_IP)
    owner_code = sender.codes[-1]

    request_code(PHONE, NOW + timedelta(seconds=5), sender, ip=ATTACKER_IP)

    verify_code(PHONE, owner_code, NOW + timedelta(seconds=10), challenge_id=owner.pk)


def test_attacker_wrong_guesses_do_not_lock_the_owner():
    sender = FakeSender()
    owner = request_code(PHONE, NOW, sender, ip=OWNER_IP)
    owner_code = sender.codes[-1]
    attacker = request_code(PHONE, NOW, sender, ip=ATTACKER_IP)

    for _ in range(6):
        with pytest.raises(OtpError):
            verify_code(PHONE, "999999" if owner_code != "999999" else "888888", NOW, challenge_id=attacker.pk)

    verify_code(PHONE, owner_code, NOW, challenge_id=owner.pk)


def test_code_only_works_for_the_challenge_it_was_issued_to():
    sender = FakeSender()
    owner = request_code(PHONE, NOW, sender, ip=OWNER_IP)
    attacker = request_code(PHONE, NOW, sender, ip=ATTACKER_IP)

    with pytest.raises(OtpError):
        verify_code(PHONE, sender.codes[0], NOW, challenge_id=attacker.pk)
    verify_code(PHONE, sender.codes[0], NOW, challenge_id=owner.pk)


def test_frequent_limits_are_per_phone_and_address():
    sender = FakeSender()
    request_code(PHONE, NOW, sender, ip=ATTACKER_IP)
    with pytest.raises(OtpError):
        request_code(PHONE, NOW + timedelta(seconds=10), sender, ip=ATTACKER_IP)

    request_code(PHONE, NOW + timedelta(seconds=10), sender, ip=OWNER_IP)


def test_overall_daily_cap_per_phone_bounds_sms_and_guesses():
    sender = FakeSender()
    for index in range(MAX_PER_PHONE_PER_DAY):
        request_code(PHONE, NOW, sender, ip=f"10.0.{index}.1")

    with pytest.raises(OtpError) as exc:
        request_code(PHONE, NOW, sender, ip="10.9.9.9")
    assert exc.value.code == "too_many"


def test_new_code_from_the_same_challenge_owner_replaces_the_old_one():
    sender = FakeSender()
    first = request_code(PHONE, NOW, sender, ip=OWNER_IP)
    second = request_code(PHONE, NOW + timedelta(seconds=61), sender, ip=OWNER_IP, previous_id=first.pk)

    with pytest.raises(OtpError):
        verify_code(PHONE, sender.codes[0], NOW + timedelta(seconds=62), challenge_id=first.pk)
    verify_code(PHONE, sender.codes[1], NOW + timedelta(seconds=62), challenge_id=second.pk)
