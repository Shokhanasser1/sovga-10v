"""Обработчики outbox для заказов."""

from apps.notifications.outbox import register
from apps.notifications.telegram import notify_managers


@register("order.created")
def notify_new_order(payload: dict) -> None:
    lines = "\n".join(f"• {line['name']} × {line['qty']}" for line in payload.get("lines", []))
    waiting = "\nЖдёт подтверждения поставщика" if payload.get("status") == "sourcing" else ""
    notify_managers(
        f"Новый заказ {payload['number']} на {payload['total']} сум{waiting}\n{lines}".strip()
    )
