"""Учебная имитация провайдеров: те же вызовы, что делают Payme и Click, но из нашего же сервера.

Заказ проходит через настоящие обработчики протоколов (payme.handle, click.prepare/complete) —
так ученики видят и отлаживают ровно тот код, что работает с настоящими деньгами.
"""

import secrets
from datetime import datetime

from django.conf import settings

from apps.orders.models import Order

from . import click, payme
from .models import Payment

CLICK_DEMO_SECRET = "demo-secret"  # подпись имитации; настоящие запросы Click проверяются ключом из настроек


def _ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _payme(method: str, params: dict, now: datetime) -> str:
    """Вызов Merchant API так, как его делает Payme. Пустая строка — успех, иначе текст ошибки."""
    response = payme.handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, now)
    error = response.get("error")
    return error["message"]["ru"] if error else ""


def simulate_payme(order: Order, action: str, now: datetime) -> str:
    if action == "refund":
        payment = Payment.objects.filter(order=order, provider=Payment.Provider.PAYME, state=Payment.State.PAID).first()
        if payment is None:
            return "Нет проведённой оплаты через Payme"
        return _payme("CancelTransaction", {"id": payment.external_id, "reason": 5}, now)
    transaction_id = f"demo-{secrets.token_hex(8)}"
    amount = order.total_uzs * 100
    account = {settings.PAYME_ACCOUNT_FIELD: order.number}
    steps = [
        ("CheckPerformTransaction", {"amount": amount, "account": account}),
        ("CreateTransaction", {"id": transaction_id, "time": _ms(now), "amount": amount, "account": account}),
        ("PerformTransaction", {"id": transaction_id}) if action == "pay"
        else ("CancelTransaction", {"id": transaction_id, "reason": 3}),
    ]
    for method, params in steps:
        if error := _payme(method, params, now):
            return error
    return ""


def simulate_click(order: Order, action: str, now: datetime) -> str:
    params = {
        "click_trans_id": str(secrets.randbelow(10**9)), "service_id": "demo", "merchant_trans_id": order.number,
        "amount": f"{order.total_uzs}.00", "action": "0", "error": "0", "sign_time": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
    params["sign_string"] = click.sign(params, CLICK_DEMO_SECRET)
    prepared = click.prepare(params, now, secret=CLICK_DEMO_SECRET)
    if prepared["error"] != click.SUCCESS:
        return _click_error(prepared["error"])
    prepare_id = str(prepared["merchant_prepare_id"])
    params = {**params, "action": "1", "merchant_prepare_id": prepare_id, "error": "0" if action == "pay" else "-5017"}
    params["sign_string"] = click.sign(params, CLICK_DEMO_SECRET, prepare_id)
    completed = click.complete(params, now, secret=CLICK_DEMO_SECRET)
    expected = click.SUCCESS if action == "pay" else click.CANCELLED  # отказ покупателя Click сообщает ошибкой
    return "" if completed["error"] == expected else _click_error(completed["error"])


def _click_error(code: int) -> str:
    return {
        click.ALREADY_PAID: "Заказ уже оплачен",
        click.CANCELLED: "Заказ нельзя оплатить",
        click.BAD_REQUEST: "Заказ уже оплачивается другим способом",
    }.get(code, f"Click ответил ошибкой {code}")


SIMULATORS = {"payme": simulate_payme, "click": simulate_click}
ACTIONS = {"payme": ("pay", "decline", "refund"), "click": ("pay", "decline")}
