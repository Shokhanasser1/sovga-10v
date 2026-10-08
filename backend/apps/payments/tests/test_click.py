import hashlib

import pytest

from apps.orders.models import Order
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

PREPARE = "/api/v1/payments/click/prepare/"
COMPLETE = "/api/v1/payments/click/complete/"
SECRET = "click-secret"
SERVICE = "12345"
S = Order.Status


@pytest.fixture(autouse=True)
def click_settings(settings):
    settings.CLICK_SECRET_KEY = SECRET
    settings.CLICK_SERVICE_ID = SERVICE


def signed(action, order_number, amount, click_trans_id="555", prepare_id="", error="0"):
    sign_time = "2026-10-08 15:00:00"
    raw = f"{click_trans_id}{SERVICE}{SECRET}{order_number}{prepare_id}{amount}{action}{sign_time}"
    data = {
        "click_trans_id": click_trans_id,
        "service_id": SERVICE,
        "click_paydoc_id": "777",
        "merchant_trans_id": order_number,
        "amount": amount,
        "action": str(action),
        "error": error,
        "error_note": "Success",
        "sign_time": sign_time,
        "sign_string": hashlib.md5(raw.encode()).hexdigest(),
    }
    if prepare_id:
        data["merchant_prepare_id"] = prepare_id
    return data


def amount(order):
    return f"{order.total_uzs}.00"


def prepare(client, order, **overrides):
    data = {**signed(0, order.number, amount(order)), **overrides}
    return client.post(PREPARE, data).json()


def complete(client, order, prepare_id, error="0"):
    return client.post(COMPLETE, signed(1, order.number, amount(order), prepare_id=str(prepare_id), error=error)).json()


def test_prepare_then_complete_marks_paid(client, order):
    prepared = prepare(client, order)

    assert prepared["error"] == 0
    order.refresh_from_db()
    assert order.status == S.AWAITING_PAYMENT
    completed = complete(client, order, prepared["merchant_prepare_id"])
    assert completed["error"] == 0 and completed["merchant_confirm_id"] == prepared["merchant_prepare_id"]
    order.refresh_from_db()
    assert order.status == S.PAID
    assert complete(client, order, prepared["merchant_prepare_id"])["error"] == -4


def test_bad_signature(client, order):
    assert prepare(client, order, sign_string="0" * 32)["error"] == -1
    assert not Payment.objects.exists()


def test_wrong_amount(client, order):
    data = signed(0, order.number, "1000.00")

    assert client.post(PREPARE, data).json()["error"] == -2


def test_unknown_order(client, order):
    assert client.post(PREPARE, signed(0, "SG999999", amount(order))).json()["error"] == -5


def test_wrong_action(client, order):
    assert client.post(PREPARE, signed(1, order.number, amount(order))).json()["error"] == -3


def test_paid_order_cannot_be_prepared_again(client, order):
    prepared = prepare(client, order)
    complete(client, order, prepared["merchant_prepare_id"])

    assert prepare(client, order, click_trans_id="556", sign_string=signed(0, order.number, amount(order), click_trans_id="556")["sign_string"])["error"] == -4


def test_unknown_prepare_id(client, order):
    prepare(client, order)

    assert complete(client, order, 999)["error"] == -6


def test_failed_payment_cancels_the_transaction(client, order):
    prepared = prepare(client, order)

    response = complete(client, order, prepared["merchant_prepare_id"], error="-5017")

    assert response["error"] == -9
    order.refresh_from_db()
    assert order.status == S.CONFIRMED
    assert Payment.objects.get().state == Payment.State.CANCELLED


def test_not_configured_secret_rejects_everything(client, order, settings):
    settings.CLICK_SECRET_KEY = ""

    assert prepare(client, order)["error"] == -1
