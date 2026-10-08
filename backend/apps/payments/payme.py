"""Payme Merchant API (JSON-RPC 2.0): Payme вызывает наш сервер, мы отвечаем result или error.

Суммы — в тийинах (сум × 100), время — в миллисекундах. Состояния транзакции Payme:
1 — создана, 2 — проведена, −1 — отменена до проведения, −2 — отменена после проведения.
Протокол взят из документации Payme; перед запуском проверить в песочнице (test.paycom.uz).
"""

from datetime import datetime

from django.conf import settings
from django.db import transaction

from apps.orders.models import Order
from apps.orders.services import OrderError

from .models import Payment
from .services import PAYABLE, confirm_payment, fail_payment, refund_payment, start_payment

TIMEOUT_MS = 12 * 60 * 60 * 1000
TIMEOUT_REASON = 4
STATE_CODE = {
    Payment.State.CREATED: 1,
    Payment.State.PAID: 2,
    Payment.State.CANCELLED: -1,
    Payment.State.REFUNDED: -2,
}


class PaymeError(Exception):
    """Ошибка протокола. commit=True — изменения, сделанные до ошибки, нужно сохранить (тайм-аут)."""

    def __init__(self, code: int, ru: str, uz: str, en: str, data: str | None = None, commit: bool = False):
        super().__init__(en)
        self.code = code
        self.message = {"ru": ru, "uz": uz, "en": en}
        self.data = data
        self.commit = commit

    def payload(self) -> dict:
        error = {"code": self.code, "message": self.message}
        if self.data:
            error["data"] = self.data
        return error


def _ms(moment: datetime | None) -> int:
    return int(moment.timestamp() * 1000) if moment else 0


def _account_field() -> str:
    return settings.PAYME_ACCOUNT_FIELD


def _not_performable(commit: bool = False) -> PaymeError:
    return PaymeError(
        -31008, "Невозможно выполнить операцию", "Amalni bajarib boʻlmaydi", "Unable to perform operation",
        commit=commit,
    )


def _order(params: dict) -> Order:
    account = params.get("account")
    number = account.get(_account_field()) if isinstance(account, dict) else None
    order = Order.objects.filter(number=number).first() if isinstance(number, str) else None
    if order is None:
        raise PaymeError(-31050, "Заказ не найден", "Buyurtma topilmadi", "Order not found", data=_account_field())
    return order


def _check_order(order: Order, params: dict) -> None:
    if order.status not in PAYABLE:
        raise PaymeError(
            -31051, "Этот заказ нельзя оплатить", "Bu buyurtmani toʻlab boʻlmaydi", "Order cannot be paid",
            data=_account_field(),
        )
    amount = params.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount != order.total_uzs * 100:
        raise PaymeError(-31001, "Неверная сумма", "Notoʻgʻri summa", "Invalid amount")


def _payment(params: dict) -> Payment:
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(provider=Payment.Provider.PAYME, external_id=str(params.get("id")))
        .first()
    )
    if payment is None:
        raise PaymeError(-31003, "Транзакция не найдена", "Tranzaksiya topilmadi", "Transaction not found")
    return payment


def receipt(order: Order) -> dict:
    """Данные для фискального чека: ИКПУ и код упаковки по каждой позиции, подарок — с ценой 0."""
    items = []
    for line in order.lines.select_related("variant__product_model"):
        items.append(
            {
                "title": line.variant.product_model.name_ru[:128],
                "price": line.price_uzs * 100,
                "count": line.qty,
                "code": line.variant.mxik_code,
                "package_code": line.variant.package_code,
                "vat_percent": settings.FISCAL_VAT_PERCENT,
                "discount": 0,
            }
        )
    return {"receipt_type": 0, "items": items}


def _expire(payment: Payment, now: datetime) -> None:
    payment.state = Payment.State.CANCELLED
    payment.cancelled_at = now
    payment.cancel_reason = TIMEOUT_REASON
    payment.save(update_fields=["state", "cancelled_at", "cancel_reason"])
    fail_payment(payment.order, now, actor="payme")


def _timed_out(payment: Payment, now: datetime) -> bool:
    return _ms(now) - _ms(payment.created_at) > TIMEOUT_MS


def check_perform_transaction(params: dict, now: datetime) -> dict:
    order = _order(params)
    _check_order(order, params)
    return {"allow": True, "detail": receipt(order)}


def create_transaction(params: dict, now: datetime) -> dict:
    existing = (
        Payment.objects.select_for_update()
        .filter(provider=Payment.Provider.PAYME, external_id=str(params.get("id")))
        .first()
    )
    if existing:
        if existing.state != Payment.State.CREATED:
            raise _not_performable()
        if _timed_out(existing, now):
            _expire(existing, now)
            raise _not_performable(commit=True)
        return {"create_time": _ms(existing.created_at), "transaction": str(existing.pk), "state": 1}
    order = _order(params)
    _check_order(order, params)
    if Payment.objects.filter(order=order, state=Payment.State.CREATED).exists():
        raise PaymeError(
            -31052, "Заказ уже оплачивается другой транзакцией", "Buyurtma boshqa tranzaksiya bilan toʻlanmoqda",
            "Order is being paid by another transaction", data=_account_field(),
        )
    payment = Payment.objects.create(
        order=order, provider=Payment.Provider.PAYME, external_id=str(params.get("id")),
        amount_uzs=order.total_uzs, provider_time=params.get("time"), created_at=now, raw=params,
    )
    try:
        start_payment(order, now, actor="payme")
    except OrderError as error:
        raise PaymeError(-31051, error.message, "Buyurtmani toʻlab boʻlmaydi", "Order cannot be paid") from error
    return {"create_time": _ms(now), "transaction": str(payment.pk), "state": 1}


def perform_transaction(params: dict, now: datetime) -> dict:
    payment = _payment(params)
    if payment.state == Payment.State.PAID:
        return {"transaction": str(payment.pk), "perform_time": _ms(payment.performed_at), "state": 2}
    if payment.state != Payment.State.CREATED:
        raise _not_performable()
    if _timed_out(payment, now):
        _expire(payment, now)
        raise _not_performable(commit=True)
    try:
        confirm_payment(payment.order, now, actor="payme", provider="Payme")
    except OrderError as error:
        raise _not_performable() from error
    payment.state = Payment.State.PAID
    payment.performed_at = now
    payment.save(update_fields=["state", "performed_at"])
    return {"transaction": str(payment.pk), "perform_time": _ms(now), "state": 2}


def cancel_transaction(params: dict, now: datetime) -> dict:
    payment = _payment(params)
    if payment.state == Payment.State.CREATED:
        payment.state = Payment.State.CANCELLED
        fail_payment(payment.order, now, actor="payme")
    elif payment.state == Payment.State.PAID:
        try:
            refund_payment(payment.order, now, actor="payme")
        except OrderError as error:
            raise PaymeError(
                -31007, "Заказ уже передан курьеру — отменить нельзя", "Buyurtma kuryerga topshirilgan",
                "Order already shipped, cannot cancel",
            ) from error
        payment.state = Payment.State.REFUNDED
    else:
        return {"transaction": str(payment.pk), "cancel_time": _ms(payment.cancelled_at), "state": STATE_CODE[payment.state]}
    payment.cancelled_at = now
    payment.cancel_reason = params.get("reason") if isinstance(params.get("reason"), int) else None
    payment.save(update_fields=["state", "cancelled_at", "cancel_reason"])
    return {"transaction": str(payment.pk), "cancel_time": _ms(now), "state": STATE_CODE[payment.state]}


def _details(payment: Payment) -> dict:
    return {
        "create_time": _ms(payment.created_at),
        "perform_time": _ms(payment.performed_at),
        "cancel_time": _ms(payment.cancelled_at),
        "transaction": str(payment.pk),
        "state": STATE_CODE[payment.state],
        "reason": payment.cancel_reason,
    }


def check_transaction(params: dict, now: datetime) -> dict:
    return _details(_payment(params))


def get_statement(params: dict, now: datetime) -> dict:
    start, end = params.get("from"), params.get("to")
    payments = Payment.objects.filter(
        provider=Payment.Provider.PAYME, provider_time__gte=start, provider_time__lte=end
    ).select_related("order")
    return {
        "transactions": [
            {
                "id": payment.external_id,
                "time": payment.provider_time,
                "amount": payment.amount_uzs * 100,
                "account": {_account_field(): payment.order.number},
                **_details(payment),
                "receivers": None,
            }
            for payment in payments.order_by("provider_time")
        ]
    }


METHODS = {
    "CheckPerformTransaction": check_perform_transaction,
    "CreateTransaction": create_transaction,
    "PerformTransaction": perform_transaction,
    "CancelTransaction": cancel_transaction,
    "CheckTransaction": check_transaction,
    "GetStatement": get_statement,
}


def error_response(request_id, code: int, ru: str, en: str) -> dict:
    return {"error": PaymeError(code, ru, ru, en).payload(), "id": request_id}


def handle(body: object, now: datetime) -> dict:
    """Один JSON-RPC вызов. Ошибки протокола — без изменений в базе, кроме явно помеченных commit=True."""
    if not isinstance(body, dict):
        return error_response(None, -32600, "Неверный запрос", "Invalid request")
    request_id = body.get("id")
    method, params = body.get("method"), body.get("params")
    if not isinstance(method, str) or not isinstance(params, dict):
        return error_response(request_id, -32600, "Неверный запрос", "Invalid request")
    handler = METHODS.get(method)
    if handler is None:
        return error_response(request_id, -32601, "Метод не найден", "Method not found")
    with transaction.atomic():
        try:
            return {"result": handler(params, now), "id": request_id}
        except PaymeError as error:
            if not error.commit:
                transaction.set_rollback(True)
            return {"error": error.payload(), "id": request_id}
