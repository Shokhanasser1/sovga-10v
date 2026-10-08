"""Ответы поставщиков «есть ли товар»: кнопки в боте, новая цена сообщением, алерт о молчании."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction

from apps.catalog.labels import variant_title
from apps.notifications.outbox import emit
from apps.sourcing.models import Offer

from .models import Order, OrderLine, SupplierRequest
from .services import confirm_sourcing, transition

S = Order.Status
R = SupplierRequest.Status
SILENCE = timedelta(minutes=30)
OPEN = {R.PENDING, R.AWAITING_PRICE}
# Только ASCII-цифры: Decimal принял бы и «٩٨٥».
PRICE = re.compile(r"^\$?\s*(\d{1,6}(?:[.,]\d{1,2})?)\s*\$?$", re.ASCII)


class RequestError(Exception):
    """Сообщение безопасно показать поставщику."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Reply:
    text: str
    final: bool  # запрос закрыт — кнопки под сообщением больше не нужны


def supplier_lines(request: SupplierRequest) -> list[OrderLine]:
    return [
        line for line in request.order.lines.select_related("variant__product_model__category", "offer")
        if line.offer and line.offer.supplier_id == request.supplier_id
    ]


def lines_payload(request: SupplierRequest) -> list[dict]:
    return [
        {"name": variant_title(line.variant), "qty": line.qty, "cost": f"{line.cost_usd:.2f}"}
        for line in supplier_lines(request)
    ]


def _close(request: SupplierRequest, status: str, now: datetime) -> None:
    request.status = status
    request.answered_at = now
    request.save(update_fields=["status", "answered_at"])


@transaction.atomic
def answer_request(request_id: int, chat_id: int, choice: str, now: datetime) -> Reply:
    request = (
        SupplierRequest.objects.select_for_update().select_related("supplier", "order").filter(pk=request_id).first()
    )
    if request is None or request.supplier.telegram_chat_id != chat_id:
        raise RequestError("Этот заказ адресован не вам")
    if request.order.status != S.SOURCING or request.status not in OPEN:
        raise RequestError("По этому заказу уже есть ответ — спасибо!")
    actor = f"supplier:{request.supplier_id}"
    if choice == "yes":
        _close(request, R.CONFIRMED, now)
        if request.order.supplier_requests.exclude(status=R.CONFIRMED).exists():
            return Reply("✅ Есть — ждём ответа других поставщиков по заказу", final=True)
        confirm_sourcing(request.order, now, actor)
        return Reply("✅ Есть — заказ подтверждён, покупатель может оплачивать", final=True)
    if choice == "no":
        _close(request, R.DECLINED, now)
        Offer.objects.filter(pk__in=[line.offer_id for line in supplier_lines(request)]).update(
            qty_available=0, last_confirmed_at=now
        )
        transition(request.order, S.CANCELLED, now, actor, note="Нет в наличии у поставщика", allowed_from={S.SOURCING})
        emit("sourcing.declined", {"number": request.order.number, "supplier": request.supplier.name}, now)
        return Reply("❌ Нет в наличии — заказ отменён, остаток у нас обнулён", final=True)
    if choice == "price":
        request.status = R.AWAITING_PRICE
        request.save(update_fields=["status"])
        return Reply("Напишите цену в долларах за 1 шт. одним числом, например 985 или 985.50", final=False)
    raise RequestError("Не понял ответ — нажмите одну из кнопок")


@transaction.atomic
def offer_price(chat_id: int, text: str, now: datetime) -> str | None:
    """Цена сообщением после кнопки «Другая цена». None — из этого чата цену сейчас не ждём."""
    request = (
        SupplierRequest.objects.select_for_update()
        .select_related("supplier", "order")
        .filter(supplier__telegram_chat_id=chat_id, status=R.AWAITING_PRICE, order__status=S.SOURCING)
        .order_by("-pk")
        .first()
    )
    if request is None:
        return None
    match = PRICE.match(text.strip())
    cost = Decimal(match.group(1).replace(",", ".")) if match else Decimal(0)
    if cost <= 0:
        return "Нужна цена числом в долларах за 1 шт., например 985 или 985.50"
    request.proposed_cost_usd = cost
    request.save(update_fields=["proposed_cost_usd"])
    _close(request, R.PRICE_OFFERED, now)
    emit(
        "sourcing.price_offered",
        {"number": request.order.number, "supplier": request.supplier.name, "cost": f"{cost:.2f}",
         "lines": lines_payload(request)},
        now,
    )
    return f"Спасибо! Передали менеджеру цену ${cost:.2f} — он подтвердит или отменит заказ."


def alert_silent_requests(now: datetime) -> int:
    """Поставщик не ответил за 30 минут — один раз сообщаем менеджерам."""
    silent = SupplierRequest.objects.filter(
        status__in=OPEN, order__status=S.SOURCING, sent_at__lte=now - SILENCE, alerted_at__isnull=True
    ).select_related("order", "supplier")
    alerted = 0
    for request in silent:
        with transaction.atomic():
            if not SupplierRequest.objects.filter(pk=request.pk, alerted_at__isnull=True).update(alerted_at=now):
                continue  # уже сообщил другой процесс
            minutes = int((now - request.sent_at).total_seconds() // 60)
            emit(
                "sourcing.silent",
                {"number": request.order.number, "supplier": request.supplier.name, "minutes": minutes},
                now,
            )
            alerted += 1
    return alerted
