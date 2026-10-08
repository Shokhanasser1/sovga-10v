"""Обработчики outbox для заказов."""

from apps.notifications.outbox import register
from apps.notifications.telegram import notify_managers


def _sum(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


@register("order.created")
def notify_new_order(payload: dict) -> None:
    lines = "\n".join(
        f"• {line['name']} × {line['qty']}{' (подарок)' if line.get('gift') else ''}"
        for line in payload.get("lines", [])
    )
    waiting = "\nЖдёт подтверждения поставщика" if payload.get("status") == "sourcing" else ""
    notify_managers(f"Новый заказ {payload['number']} на {_sum(payload['total'])} сум{waiting}\n{lines}")
