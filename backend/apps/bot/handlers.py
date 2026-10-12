"""Обработчики outbox, которые пишут в Telegram от имени бота."""

from django.conf import settings
from django.utils import timezone

from apps.catalog.labels import variant_title
from apps.delivery.models import Shipment
from apps.notifications.outbox import register
from apps.notifications.telegram import notify_managers, send_message, simulated
from apps.orders.models import Order, SupplierRequest
from apps.orders.supplier_requests import OPEN, supplier_lines
from apps.sourcing.models import SupplierSkuMap

from . import texts


def request_text(request: SupplierRequest) -> str:
    codes = dict(
        SupplierSkuMap.objects.filter(supplier=request.supplier).values_list("variant_id", "supplier_code")
    )
    lines = []
    for line in supplier_lines(request):
        code = f" (ваш арт. {codes[line.variant_id]})" if line.variant_id in codes else ""
        lines.append(f"• {variant_title(line.variant)} × {line.qty} — ${line.cost_usd:.2f}{code}")
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


def _is_quiet(previous: str | None, status: str) -> bool:
    """Не пишем технические шаги оплаты (покупатель сам на странице оплаты) и «Завершён» по истечении срока возврата."""
    S = Order.Status
    return (
        status == S.AWAITING_PAYMENT
        or (status == S.CONFIRMED and previous == S.AWAITING_PAYMENT)
        or (status == S.COMPLETED and previous == S.DELIVERED)
    )


def status_text(order: Order, previous: str | None, status: str, note: str) -> str:
    S = Order.Status
    language = order.customer.language
    words = texts.for_language(language)
    lines = [words["status"].format(number=order.number, status=texts.status_label(language, status))]
    if status == S.CONFIRMED:
        lines.append(words["pay_now"])
    elif status == S.PAID:
        lines.append(words["paid"])
    elif status == S.HANDED_TO_CARRIER and (shipment := Shipment.objects.filter(order=order).first()):
        if shipment.carrier == Shipment.Carrier.OWN:
            lines.append(words["courier"].format(name=shipment.courier_name, phone=shipment.courier_phone))
        else:
            lines.append(words["service"].format(service=shipment.service_name, tracking=shipment.tracking))
    elif status == S.CANCELLED:
        if previous in (S.AWAITING_PAYMENT, S.PAID, S.PICKING):
            lines.append(words["refund"])
        if note and words["reason"]:  # причины записаны по-русски — узбекским покупателям не показываем
            lines.append(words["reason"].format(note=note))
    elif status in (S.RETURN_REQUESTED, S.INSPECTED, S.REFUNDED, S.COMPLETED) and note and words["reason"]:
        lines.append(note)  # «Причина: …», «К возврату … сум», «Деньги возвращены: … сум»
    lines.append(f"{settings.SITE_URL.rstrip('/')}/{language}/orders/{order.number}")
    return "\n".join(lines)


@register("order.status")
def notify_customer(payload: dict) -> None:
    if _is_quiet(payload.get("from"), payload["to"]) or not (settings.TELEGRAM_BOT_TOKEN or simulated()):
        return
    order = Order.objects.select_related("customer").filter(number=payload["number"]).first()
    if order is None or not order.customer.telegram_chat_id:
        return
    send_message(
        order.customer.telegram_chat_id, status_text(order, payload.get("from"), payload["to"], payload.get("note", ""))
    )


@register("fulfilment.started")
def ask_suppliers_for_imei(payload: dict) -> None:
    """Заказ собирается — поставщики с поштучным товаром везут устройства и присылают IMEI."""
    order = Order.objects.filter(number=payload["number"], status=Order.Status.PICKING).first()
    if order is None:
        return
    by_supplier: dict = {}
    for line in order.lines.select_related("offer__supplier", "variant__product_model__category"):
        supplier = line.offer.supplier if line.offer else None
        if supplier and supplier.telegram_chat_id and line.variant.product_model.category.is_serialized:
            by_supplier.setdefault(supplier, []).append(f"• {variant_title(line.variant)} × {line.qty}")
    for supplier, lines in by_supplier.items():
        send_message(supplier.telegram_chat_id, "\n".join([
            f"Заказ {order.number} оплачен и собирается — привезите, пожалуйста:", *lines,
            "Пришлите IMEI каждого устройства отдельным сообщением (15 цифр). "
            f"Если заказов несколько, можно так: {order.number} 356938035643809",
        ]))
