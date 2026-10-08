"""Входящие обновления Telegram: команды покупателей, кнопки и цены поставщиков, /id для менеджеров."""

import re
from datetime import datetime

from apps.customers.models import Customer
from apps.notifications import telegram
from apps.notifications.telegram import send_message
from apps.orders.fulfilment import add_supplier_unit
from apps.orders.supplier_requests import RequestError, answer_request, offer_price

from . import texts
from .links import redeem
from .models import TelegramLink

# IMEI от поставщика: «356938035643809» или «SG000013 356938035643809» (пробелы не важны).
IMEI_MESSAGE = re.compile(r"^(SG\d{6})?(\d{15})$", re.ASCII)


def handle_update(update: dict, now: datetime) -> None:
    if query := update.get("callback_query"):
        on_callback(query, now)
        return
    message = update.get("message")
    if message and isinstance(message.get("text"), str):
        on_message(message["chat"]["id"], message["text"].strip(), now)


def on_callback(query: dict, now: datetime) -> None:
    """Кнопка под запросом поставщику: sr:<номер запроса>:yes|no|price."""
    message = query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    kind, _, rest = str(query.get("data") or "").partition(":")
    request_id, _, choice = rest.partition(":")
    try:
        if kind != "sr" or chat_id is None or not (request_id.isascii() and request_id.isdigit()):
            raise RequestError("Кнопка устарела")
        reply = answer_request(int(request_id), chat_id, choice, now)
    except RequestError as error:
        telegram.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": error.message, "show_alert": True})
        return
    telegram.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": reply.text[:200]})
    if reply.final:
        text = f"{message.get('text', '')}\n\n{reply.text}"
        telegram.call("editMessageText", {"chat_id": chat_id, "message_id": message.get("message_id"), "text": text})
    else:
        send_message(chat_id, reply.text)


def on_message(chat_id: int, text: str, now: datetime) -> None:
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()  # в группах команды приходят как /id@имя_бота
    if command == "/start":
        reply = _start(chat_id, argument.strip(), now)
    elif command == "/orders":
        reply = _orders(chat_id)
    elif command == "/stop":
        reply = _stop(chat_id)
    elif command == "/id":
        reply = texts.CHAT_ID.format(chat_id=chat_id)
    elif match := IMEI_MESSAGE.match(text.replace(" ", "").upper()):
        reply = add_supplier_unit(chat_id, match.group(2), match.group(1) or "", now) or texts.HELP
    else:
        reply = offer_price(chat_id, text, now) or texts.HELP
    send_message(chat_id, reply)


def _start(chat_id: int, payload: str, now: datetime) -> str:
    if not payload:
        return texts.HELP
    link = redeem(payload, chat_id, now)
    if link is None:
        return texts.BAD_LINK
    if link.kind == TelegramLink.Kind.SUPPLIER:
        return texts.SUPPLIER_LINKED.format(name=link.supplier.name)
    return texts.for_language(link.customer.language)["linked"]


def _orders(chat_id: int) -> str:
    customer = Customer.objects.filter(telegram_chat_id=chat_id).first()
    if customer is None:
        return texts.NOT_LINKED
    words = texts.for_language(customer.language)
    orders = list(customer.orders.all()[:5])
    if not orders:
        return words["no_orders"]
    lines = [
        words["order_line"].format(
            number=order.number, status=texts.status_label(customer.language, order.status),
            total=texts.money(order.total_uzs),
        )
        for order in orders
    ]
    return "\n".join([words["orders"], *lines])


def _stop(chat_id: int) -> str:
    customer = Customer.objects.filter(telegram_chat_id=chat_id).first()
    if customer is None:
        return texts.NOT_LINKED
    customer.telegram_chat_id = None
    customer.save(update_fields=["telegram_chat_id"])
    return texts.for_language(customer.language)["unlinked"]
