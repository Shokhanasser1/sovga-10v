"""Оформление заказа и все смены его статуса."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction

from apps.catalog.models import Variant
from apps.customers.models import Customer
from apps.notifications.outbox import emit
from apps.sourcing.models import Offer, Reservation, Supplier
from apps.sourcing.reservations import release, reserve

from .models import Order, OrderEvent, OrderLine
from .quote import CartItem, Quote, QuoteLine, quote
from .state import CUSTOMER_CANCELLABLE, can_transition

S = Order.Status
PRICE_LOCK = timedelta(minutes=30)
SOURCING_SLA = timedelta(hours=2)


class OrderError(Exception):
    """Сообщение безопасно показывать покупателю."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class DeliveryAddress:
    text: str
    landmark: str = ""


def _needs_supplier_confirmation(offer: Offer) -> bool:
    """Свой склад и поставщик с API — остатки надёжные; таблица и Telegram — нужно подтверждение."""
    return not offer.is_own and offer.supplier.connector_type != Supplier.Connector.API


def _quote_problems(result: Quote) -> str:
    messages = list(result.errors)
    for line in result.lines:
        messages += [message for message in line.errors if message not in messages]
    return "; ".join(messages)


def _reserve_line(order: Order, line: QuoteLine, now: datetime) -> tuple[OrderLine, bool]:
    reservation = reserve(line.variant, line.qty, order.number, now, SOURCING_SLA)
    if reservation is None:
        raise OrderError(f"«{line.variant.product_model.name_ru}» только что закончился — обновите корзину")
    main = OrderLine.objects.create(
        order=order, variant=line.variant, qty=line.qty, price_uzs=line.unit_price_uzs,
        cost_usd=reservation.offer.cost_usd, offer=reservation.offer, reservation=reservation,
    )
    if line.gift:
        gift_variant = Variant.objects.get(sku=line.gift.sku)
        gift_reservation = reserve(gift_variant, line.qty, order.number, now, SOURCING_SLA)
        if gift_reservation is None or not gift_reservation.offer.is_own:
            raise OrderError("Выбранный подарок только что закончился — выберите другой")
        OrderLine.objects.create(
            order=order, variant=gift_variant, qty=line.qty, price_uzs=0,
            cost_usd=gift_reservation.offer.cost_usd, offer=gift_reservation.offer,
            reservation=gift_reservation, is_gift=True, gift_for=main,
        )
    return main, _needs_supplier_confirmation(reservation.offer)


def _created_payload(order: Order) -> dict:
    lines = [
        {"name": line.variant.product_model.name_ru, "sku": line.variant.sku, "qty": line.qty, "gift": line.is_gift}
        for line in order.lines.select_related("variant__product_model")
    ]
    return {"number": order.number, "status": order.status, "total": order.total_uzs, "lines": lines}


@transaction.atomic
def create_order(
    customer: Customer,
    items: list[CartItem],
    payment_method: str,
    address: DeliveryAddress,
    comment: str,
    now: datetime,
) -> Order:
    """Проверяет корзину тем же расчётом, что видел покупатель, резервирует товар и подарки.

    Любая ошибка откатывает всё: заказ, строки и резервы.
    """
    result = quote(items, payment_method, now)
    if not result.can_order:
        raise OrderError(_quote_problems(result))
    rate = result.lines[0].variant.price_snapshots.order_by("-computed_at", "-pk").first().rate
    order = Order.objects.create(
        customer=customer, status=S.SOURCING, payment_method=payment_method, address_text=address.text,
        address_landmark=address.landmark, comment=comment, total_uzs=result.total_uzs, rate=rate,
        price_lock_until=now + PRICE_LOCK,
    )
    order.number = f"SG{order.pk:06d}"
    order.save(update_fields=["number"])
    needs_confirmation = False
    for line in result.lines:
        _, needs = _reserve_line(order, line, now)
        needs_confirmation = needs_confirmation or needs
    if needs_confirmation:
        order.sla_deadline = now + SOURCING_SLA
    else:
        order.status = S.CONFIRMED
        Reservation.objects.filter(ref=order.number).update(expires_at=order.price_lock_until)
    order.save(update_fields=["status", "sla_deadline"])
    OrderEvent.objects.create(
        order=order, status_to=order.status, actor=f"customer:{customer.phone}", note="Заказ оформлен", created_at=now
    )
    emit("order.created", _created_payload(order), now)
    return order


@transaction.atomic
def transition(
    order: Order,
    target: str,
    now: datetime,
    actor: str,
    note: str = "",
    allowed_from: set[str] | None = None,
    denied_message: str = "",
) -> Order:
    """Все проверки — по свежему статусу под блокировкой, а не по объекту, загруженному раньше."""
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if allowed_from is not None and locked.status not in allowed_from:
        raise OrderError(denied_message or "Сейчас это действие недоступно")
    if not can_transition(locked.status, target):
        raise OrderError(f"Нельзя перевести заказ из «{S(locked.status).label}» в «{S(target).label}»")
    previous = locked.status
    locked.status = target
    locked.save(update_fields=["status", "updated_at"])
    OrderEvent.objects.create(
        order=locked, status_from=previous, status_to=target, actor=actor, note=note, created_at=now
    )
    if target == S.CANCELLED:
        for reservation in Reservation.objects.filter(ref=locked.number, released_at__isnull=True):
            release(reservation, now)
    order.status = locked.status
    return locked


@transaction.atomic
def confirm_sourcing(order: Order, now: datetime, actor: str) -> Order:
    """Поставщик подтвердил наличие — покупатель получает 30 минут на оплату."""
    confirmed = transition(order, S.CONFIRMED, now, actor, note="Поставщик подтвердил наличие")
    confirmed.price_lock_until = now + PRICE_LOCK
    confirmed.sla_deadline = None
    confirmed.save(update_fields=["price_lock_until", "sla_deadline"])
    Reservation.objects.filter(ref=confirmed.number, released_at__isnull=True).update(
        expires_at=confirmed.price_lock_until
    )
    return confirmed


def cancel_order(order: Order, now: datetime, actor: str, note: str = "", by_customer: bool = False) -> Order:
    return transition(
        order, S.CANCELLED, now, actor, note or "Отменён",
        allowed_from=CUSTOMER_CANCELLABLE if by_customer else None,
        denied_message="Оплаченный заказ отменяет менеджер — напишите нам, деньги вернём",
    )


def expire_orders(now: datetime) -> int:
    """Неоплаченные после фиксации цены и неподтверждённые поставщиком за 2 часа — отменяем."""
    expired = [
        (order, "Не оплачен за 30 минут — резерв снят")
        for order in Order.objects.filter(status=S.CONFIRMED, price_lock_until__lt=now)
    ] + [
        (order, "Поставщик не подтвердил наличие за 2 часа")
        for order in Order.objects.filter(status=S.SOURCING, sla_deadline__lt=now)
    ]
    for order, note in expired:
        transition(order, S.CANCELLED, now, actor="system", note=note)
    return len(expired)
