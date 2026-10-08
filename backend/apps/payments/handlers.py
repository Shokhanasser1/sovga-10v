"""Обработчики outbox для платежей."""

from apps.notifications.outbox import register
from apps.notifications.telegram import notify_managers


@register("order.paid")
def notify_paid_order(payload: dict) -> None:
    total = f"{payload['total']:,}".replace(",", " ")
    notify_managers(f"Заказ {payload['number']} оплачен через {payload['provider']}: {total} сум — можно собирать")
