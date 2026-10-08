import base64
import json
from datetime import timedelta

import pytest

from apps.orders.models import Order
from apps.payments import payme
from apps.payments.models import Payment

from .conftest import MXIK_CODE, NOW

pytestmark = pytest.mark.django_db

URL = "/api/v1/payments/payme/"
KEY = "payme-test-key"
S = Order.Status


@pytest.fixture(autouse=True)
def payme_settings(settings):
    settings.PAYME_KEY = KEY
    settings.PAYME_ACCOUNT_FIELD = "order_id"
    settings.FISCAL_VAT_PERCENT = 12


def call(method, params, now=NOW, request_id=7):
    return payme.handle({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}, now)


def tiyin(order):
    return order.total_uzs * 100


def create(order, tx="tx-1", now=NOW):
    return call("CreateTransaction", {"id": tx, "time": 1, "amount": tiyin(order), "account": {"order_id": order.number}}, now)


def http(client, body, key=KEY):
    auth = base64.b64encode(f"Paycom:{key}".encode()).decode()
    return client.post(URL, body, content_type="application/json", HTTP_AUTHORIZATION=f"Basic {auth}").json()


def test_wrong_key_is_rejected(client, order):
    body = json.dumps({"id": 1, "method": "CheckTransaction", "params": {"id": "x"}})

    assert http(client, body, key="guess")["error"]["code"] == -32504
    assert client.post(URL, body, content_type="application/json").json()["error"]["code"] == -32504


def test_not_configured_key_rejects_everything(client, order, settings):
    settings.PAYME_KEY = ""
    body = json.dumps({"id": 1, "method": "CheckTransaction", "params": {"id": "x"}})

    assert http(client, body, key="")["error"]["code"] == -32504


def test_broken_json_and_unknown_method(client):
    assert http(client, "{not json")["error"]["code"] == -32700
    assert http(client, json.dumps({"id": 1, "method": "Hack", "params": {}}))["error"]["code"] == -32601


def test_check_perform_returns_fiscal_receipt(order):
    response = call("CheckPerformTransaction", {"amount": tiyin(order), "account": {"order_id": order.number}})

    result = response["result"]
    assert result["allow"] is True
    phone, gift = result["detail"]["items"]
    assert (phone["price"], phone["count"], phone["code"], phone["package_code"], phone["vat_percent"]) == (
        14_080_000 * 100, 1, MXIK_CODE, "1500", 12,
    )
    assert gift["price"] == 0
    assert response["id"] == 7


@pytest.mark.parametrize(
    "params, code",
    [
        ({"amount": 1, "account": {"order_id": "ORDER"}}, -31001),
        ({"amount": 1, "account": {"order_id": "SG999999"}}, -31050),
        ({"amount": 1, "account": {}}, -31050),
    ],
)
def test_check_perform_errors(order, params, code):
    if params["account"].get("order_id") == "ORDER":
        params["account"]["order_id"] = order.number
    response = call("CheckPerformTransaction", params)

    assert response["error"]["code"] == code
    assert set(response["error"]["message"]) == {"ru", "uz", "en"}


def test_cancelled_order_cannot_be_paid(order):
    Order.objects.filter(pk=order.pk).update(status=S.CANCELLED)

    response = call("CheckPerformTransaction", {"amount": tiyin(order), "account": {"order_id": order.number}})

    assert response["error"]["code"] == -31051


def test_create_is_idempotent_and_blocks_other_transactions(order):
    first = create(order)["result"]
    again = create(order)["result"]

    assert first["state"] == 1 and first == again
    order.refresh_from_db()
    assert order.status == S.AWAITING_PAYMENT
    assert create(order, tx="tx-2")["error"]["code"] == -31052


def test_perform_marks_the_order_paid_once(order):
    create(order)

    performed = call("PerformTransaction", {"id": "tx-1"}, NOW + timedelta(minutes=1))["result"]
    repeated = call("PerformTransaction", {"id": "tx-1"}, NOW + timedelta(minutes=2))["result"]

    assert performed["state"] == 2 and performed == repeated
    order.refresh_from_db()
    assert order.status == S.PAID


def test_unknown_transaction(order):
    assert call("PerformTransaction", {"id": "nope"})["error"]["code"] == -31003
    assert call("CheckTransaction", {"id": "nope"})["error"]["code"] == -31003


def test_timeout_cancels_the_transaction_and_keeps_the_cancellation(order):
    create(order)

    response = call("PerformTransaction", {"id": "tx-1"}, NOW + timedelta(hours=13))

    assert response["error"]["code"] == -31008
    payment = Payment.objects.get()
    assert (payment.state, payment.cancel_reason) == (Payment.State.CANCELLED, 4)
    order.refresh_from_db()
    assert order.status == S.CONFIRMED


def test_cancel_before_perform_lets_the_customer_retry(order):
    create(order)

    result = call("CancelTransaction", {"id": "tx-1", "reason": 3})["result"]

    assert result["state"] == -1
    order.refresh_from_db()
    assert order.status == S.CONFIRMED
    assert call("CancelTransaction", {"id": "tx-1", "reason": 3})["result"] == result


def test_cancel_after_perform_refunds_and_cancels_the_order(order):
    create(order)
    call("PerformTransaction", {"id": "tx-1"})

    result = call("CancelTransaction", {"id": "tx-1", "reason": 5})["result"]

    assert result["state"] == -2
    order.refresh_from_db()
    assert order.status == S.CANCELLED


def test_no_cancel_once_the_courier_has_it(order):
    create(order)
    call("PerformTransaction", {"id": "tx-1"})
    Order.objects.filter(pk=order.pk).update(status=S.HANDED_TO_CARRIER)

    assert call("CancelTransaction", {"id": "tx-1", "reason": 5})["error"]["code"] == -31007
    assert Payment.objects.get().state == Payment.State.PAID


def test_perform_fails_if_the_order_was_cancelled_meanwhile(order):
    create(order)
    Order.objects.filter(pk=order.pk).update(status=S.CANCELLED)

    assert call("PerformTransaction", {"id": "tx-1"})["error"]["code"] == -31008
    assert Payment.objects.get().state == Payment.State.CREATED


def test_check_transaction_and_statement(order):
    create(order)
    call("PerformTransaction", {"id": "tx-1"}, NOW + timedelta(minutes=1))

    check = call("CheckTransaction", {"id": "tx-1"})["result"]
    statement = call("GetStatement", {"from": 0, "to": 10})["result"]["transactions"]

    assert check["state"] == 2 and check["cancel_time"] == 0 and check["reason"] is None
    assert check["perform_time"] > check["create_time"]
    [entry] = statement
    assert (entry["id"], entry["amount"], entry["account"], entry["state"]) == (
        "tx-1", tiyin(order), {"order_id": order.number}, 2,
    )
