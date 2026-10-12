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


@register("order.cod")
def notify_cod_order(payload: dict) -> None:
    notify_managers(
        f"Заказ {payload['number']} с оплатой при получении: {_sum(payload['total'])} сум — можно собирать. "
        "Курьер возьмёт деньги при выдаче"
    )


@register("sourcing.declined")
def notify_declined(payload: dict) -> None:
    notify_managers(
        f"Заказ {payload['number']}: у поставщика «{payload['supplier']}» нет в наличии — заказ отменён, "
        "покупатель уведомлён, остаток поставщика обнулён"
    )


@register("sourcing.price_offered")
def notify_price_offered(payload: dict) -> None:
    lines = "\n".join(f"• {line['name']} × {line['qty']} — было ${line['cost']}" for line in payload.get("lines", []))
    notify_managers(
        f"Заказ {payload['number']}: поставщик «{payload['supplier']}» просит ${payload['cost']} за 1 шт.\n{lines}\n"
        "Подтвердите заказ в админке («Подтвердить у поставщика») или отмените"
    )


@register("sourcing.silent")
def notify_silent(payload: dict) -> None:
    notify_managers(
        f"Заказ {payload['number']}: поставщик «{payload['supplier']}» молчит {payload['minutes']} мин — "
        "позвоните ему или подтвердите заказ в админке"
    )


@register("order.low_margin")
def notify_low_margin(payload: dict) -> None:
    notify_managers(
        f"Заказ {payload['number']}: маржа {_sum(payload['margin'])} сум — ниже минимума {_sum(payload['minimum'])} сум. "
        "Проверьте закупку и подарок"
    )
