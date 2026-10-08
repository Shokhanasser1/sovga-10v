"""Click SHOP API: Prepare (action=0) и Complete (action=1), запросы приходят form-urlencoded.

Подпись: md5(click_trans_id + service_id + SECRET + merchant_trans_id [+ merchant_prepare_id] + amount +
action + sign_time). Суммы — в сумах. Протокол взят из документации Click; перед запуском проверить
в тестовом кабинете Click.
"""

import hashlib
import hmac
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from apps.orders.models import Order
from apps.orders.services import OrderError

from .models import Payment
from .services import PAYABLE, confirm_payment, fail_payment, start_payment

SUCCESS, SIGN_FAILED, BAD_AMOUNT, BAD_ACTION, ALREADY_PAID = 0, -1, -2, -3, -4
NO_ORDER, NO_TRANSACTION, BAD_REQUEST, CANCELLED = -5, -6, -8, -9
NOTES = {
    SUCCESS: "Success",
    SIGN_FAILED: "SIGN CHECK FAILED!",
    BAD_AMOUNT: "Incorrect parameter amount",
    BAD_ACTION: "Action not found",
    ALREADY_PAID: "Already paid",
    NO_ORDER: "User does not exist",
    NO_TRANSACTION: "Transaction does not exist",
    BAD_REQUEST: "Error in request from click",
    CANCELLED: "Transaction cancelled",
}
REQUIRED = ("click_trans_id", "service_id", "merchant_trans_id", "amount", "action", "sign_time", "sign_string")
S = Order.Status


def sign(params: dict, secret: str, prepare_id: str = "") -> str:
    raw = (
        f"{params['click_trans_id']}{params['service_id']}{secret}{params['merchant_trans_id']}"
        f"{prepare_id}{params['amount']}{params['action']}{params['sign_time']}"
    )
    # nosemgrep: python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 — алгоритм задан протоколом Click


def _signed(params: dict, prepare_id: str = "", secret: str | None = None) -> bool:
    secret = secret if secret is not None else settings.CLICK_SECRET_KEY
    if not secret:
        return False
    return hmac.compare_digest(sign(params, secret, prepare_id), str(params["sign_string"]))


def _response(params: dict, code: int, **extra) -> dict:
    return {
        "click_trans_id": params.get("click_trans_id"),
        "merchant_trans_id": params.get("merchant_trans_id"),
        "error": code,
        "error_note": NOTES[code],
        **extra,
    }


def _amount_matches(order: Order, raw: str) -> bool:
    try:
        return Decimal(str(raw)) == Decimal(order.total_uzs)
    except InvalidOperation:
        return False


def _incomplete(params: dict, *extra: str) -> bool:
    return any(not params.get(key) for key in (*REQUIRED, *extra))


@transaction.atomic
def prepare(params: dict, now: datetime, secret: str | None = None) -> dict:
    """secret — только для учебной имитации; настоящие запросы проверяются ключом из настроек."""
    if _incomplete(params):
        return _response(params, BAD_REQUEST)
    if not _signed(params, secret=secret):
        return _response(params, SIGN_FAILED)
    if params["action"] != "0":
        return _response(params, BAD_ACTION)
    order = Order.objects.select_for_update().filter(number=params["merchant_trans_id"]).first()
    if order is None:
        return _response(params, NO_ORDER)
    if order.status not in PAYABLE:
        return _response(params, ALREADY_PAID if order.status != S.CANCELLED else CANCELLED)
    if not _amount_matches(order, params["amount"]):
        return _response(params, BAD_AMOUNT)
    existing = Payment.objects.filter(provider=Payment.Provider.CLICK, external_id=params["click_trans_id"]).first()
    if existing:
        return _response(params, SUCCESS, merchant_prepare_id=existing.pk)
    active = Payment.objects.filter(order=order, state=Payment.State.CREATED)
    if active.exclude(provider=Payment.Provider.CLICK).exists():
        return _response(params, BAD_REQUEST)  # заказ уже оплачивается через Payme
    active.update(state=Payment.State.CANCELLED, cancelled_at=now)  # прошлая попытка Click брошена
    payment = Payment.objects.create(
        order=order, provider=Payment.Provider.CLICK, external_id=params["click_trans_id"],
        amount_uzs=order.total_uzs, created_at=now, raw=params,
    )
    start_payment(order, now, actor="click")
    return _response(params, SUCCESS, merchant_prepare_id=payment.pk)


def _prepared_payment(params: dict) -> Payment | None:
    try:
        prepare_id = int(params["merchant_prepare_id"])
    except (TypeError, ValueError):
        return None
    return (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(pk=prepare_id, provider=Payment.Provider.CLICK, external_id=params["click_trans_id"])
        .first()
    )


@transaction.atomic
def complete(params: dict, now: datetime, secret: str | None = None) -> dict:
    if _incomplete(params, "merchant_prepare_id"):
        return _response(params, BAD_REQUEST)
    if not _signed(params, params["merchant_prepare_id"], secret=secret):
        return _response(params, SIGN_FAILED)
    if params["action"] != "1":
        return _response(params, BAD_ACTION)
    payment = _prepared_payment(params)
    if payment is None:
        return _response(params, NO_TRANSACTION)
    if payment.state == Payment.State.PAID:
        return _response(params, ALREADY_PAID)
    if payment.state != Payment.State.CREATED:
        return _response(params, CANCELLED)
    if not _amount_matches(payment.order, params["amount"]):
        return _response(params, BAD_AMOUNT)
    click_failed = str(params.get("error", "0")).lstrip("-").isdigit() and int(params.get("error", "0")) < 0
    if not click_failed:
        try:
            confirm_payment(payment.order, now, actor="click", provider="Click")
        except OrderError:
            click_failed = True  # заказ успели отменить — Click вернёт деньги
    if click_failed:
        payment.state = Payment.State.CANCELLED
        payment.cancelled_at = now
        payment.save(update_fields=["state", "cancelled_at"])
        fail_payment(payment.order, now, actor="click")
        return _response(params, CANCELLED)
    payment.state = Payment.State.PAID
    payment.performed_at = now
    payment.save(update_fields=["state", "performed_at"])
    return _response(params, SUCCESS, merchant_confirm_id=payment.pk)
