"""Учебный режим без токена: «Имитация Telegram».

Бот работает по-настоящему — те же обработчики outbox и dispatch.handle_update, — но вместо Bot API
сообщения пишутся в таблицу DemoMessage, а отвечают на них из админки от имени чата.
"""

from apps.customers.models import Customer
from apps.notifications.telegram import DEMO_MANAGER_CHAT, manager_chats
from apps.sourcing.models import Supplier

from .models import DemoMessage

CUSTOMER_CHATS = 7_000_000_000  # учебные номера чатов: покупатель — CUSTOMER_CHATS + id
SUPPLIER_CHATS = 8_000_000_000

__all__ = ["DEMO_MANAGER_CHAT", "chats", "customer_chat", "supplier_chat", "transport"]


def customer_chat(customer: Customer) -> int:
    return CUSTOMER_CHATS + customer.pk


def supplier_chat(supplier: Supplier) -> int:
    return SUPPLIER_CHATS + supplier.pk


def transport(method: str, payload: dict):
    """Ответы как у Bot API — для тех методов, которыми пользуется магазин."""
    if method == "sendMessage":
        message = DemoMessage.objects.create(
            chat_id=int(payload["chat_id"]), direction=DemoMessage.Direction.OUT, text=payload["text"],
            reply_markup=payload.get("reply_markup"),
        )
        return {"message_id": message.pk}
    if method == "editMessageText":  # ответ поставщика: текст дополняется, кнопки убираются
        DemoMessage.objects.filter(pk=payload["message_id"], chat_id=int(payload["chat_id"])).update(
            text=payload["text"], reply_markup=None
        )
    if method == "getUpdates":
        return []
    return True


def chats() -> list[dict]:
    """Все учебные чаты: менеджеры, поставщики и покупатели с привязанным чатом, остальные — по номеру."""
    result = [{"id": int(chat), "title": "Менеджеры"} for chat in manager_chats()]
    result += [
        {"id": supplier.telegram_chat_id, "title": f"Поставщик: {supplier.name}"}
        for supplier in Supplier.objects.filter(telegram_chat_id__isnull=False).order_by("name")
    ]
    result += [
        {"id": customer.telegram_chat_id, "title": f"Покупатель: {customer.phone}"}
        for customer in Customer.objects.filter(telegram_chat_id__isnull=False).order_by("phone")
    ]
    known = {chat["id"] for chat in result}
    others = DemoMessage.objects.exclude(chat_id__in=known).values_list("chat_id", flat=True).distinct()
    return result + [{"id": chat, "title": f"Чат {chat}"} for chat in sorted(set(others))]
