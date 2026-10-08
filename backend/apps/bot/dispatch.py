"""Входящие обновления Telegram: команды покупателей, поставщиков и менеджеров."""

from datetime import datetime

from apps.customers.models import Customer
from apps.notifications.telegram import send_message

from . import texts
from .links import redeem
from .models import TelegramLink


def handle_update(update: dict, now: datetime) -> None:
    message = update.get("message")
    if message and isinstance(message.get("text"), str):
        on_message(message["chat"]["id"], message["text"].strip(), now)


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
    else:
        reply = texts.HELP
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
