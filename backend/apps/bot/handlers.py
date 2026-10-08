"""Обработчики outbox, которые пишут в Telegram от имени бота."""

from django.utils import timezone

from apps.notifications.outbox import register
from apps.notifications.telegram import notify_managers, send_message
from apps.orders.models import Order, SupplierRequest
from apps.orders.supplier_requests import OPEN, supplier_lines
from apps.sourcing.matching import variant_label
from apps.sourcing.models import SupplierSkuMap


def request_text(request: SupplierRequest) -> str:
    codes = dict(
        SupplierSkuMap.objects.filter(supplier=request.supplier).values_list("variant_id", "supplier_code")
    )
    lines = []
    for line in supplier_lines(request):
        code = f" (ваш арт. {codes[line.variant_id]})" if line.variant_id in codes else ""
        lines.append(f"• {variant_label(line.variant)} × {line.qty} — ${line.cost_usd:.2f}{code}")
    return "\n".join(
        [f"Заказ {request.order.number} — есть в наличии?", *lines, "Ответьте в течение 2 часов, иначе заказ отменится."]
    )


def keyboard(request: SupplierRequest) -> dict:
    data = f"sr:{request.pk}"
    return {
        "inline_keyboard": [
            [{"text": "✅ Есть", "callback_data": f"{data}:yes"}, {"text": "❌ Нет", "callback_data": f"{data}:no"}],
            [{"text": "💲 Другая цена", "callback_data": f"{data}:price"}],
        ]
    }


@register("sourcing.requested")
def ask_supplier(payload: dict) -> None:
    request = SupplierRequest.objects.select_related("order", "supplier").filter(pk=payload["request"]).first()
    if request is None or request.sent_at or request.status not in OPEN or request.order.status != Order.Status.SOURCING:
        return
    if request.supplier.telegram_chat_id is None:
        notify_managers(
            f"{request_text(request)}\n\nПоставщик «{request.supplier.name}» не подключён к боту — "
            "проверьте наличие вручную и нажмите в админке «Подтвердить у поставщика»"
        )
        return
    message_id = send_message(request.supplier.telegram_chat_id, request_text(request), reply_markup=keyboard(request))
    SupplierRequest.objects.filter(pk=request.pk).update(message_id=message_id, sent_at=timezone.now())
