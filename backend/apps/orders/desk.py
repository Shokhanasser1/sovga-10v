"""Рабочее место оператора: очередь заказов по этапам с таймерами и действия над заказом."""

import re
from datetime import datetime, timedelta

from django.db.models import OuterRef, Q, Subquery
from django.http import Http404

from apps.catalog.labels import variant_title
from apps.delivery.carriers import Handover
from apps.inventory.models import InventoryUnit

from .fulfilment import PICKABLE, add_unit, deliver, mark_uzimei, picking_problems, remove_unit, ship, start_picking
from .models import Order, OrderEvent, OrderLine, ReturnRequest
from .returns import inspect_return, open_return, refund_return, reject_return, return_deadline
from .services import cancel_order, confirm_sourcing, money
from .state import CANCELLABLE

S = Order.Status
PICK_WITHIN = timedelta(hours=4)  # от оплаты до передачи курьеру
SOON = timedelta(minutes=30)

# Этап: ключ, заголовок, статусы, срок, кнопка в очереди.
STAGES = [
    ("sourcing", "Ждут ответа поставщика", (S.SOURCING,), "sla_deadline", ("confirm", "Подтвердить у поставщика")),
    ("payment", "Ждут оплаты", (S.CONFIRMED, S.AWAITING_PAYMENT), "price_lock_until", None),
    ("to_pick", "К сборке", tuple(PICKABLE), "pick_deadline", ("start", "Начать сборку")),
    ("picking", "Собираются", (S.PICKING,), "pick_deadline", None),
    ("carrier", "У курьера", (S.HANDED_TO_CARRIER,), None, ("deliver", "Доставлен")),
    ("returns", "Возвраты", (S.RETURN_REQUESTED, S.INSPECTED), None, None),
]


def duration(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days} д {hours} ч"
    if hours:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def timer(deadline: datetime | None, now: datetime) -> tuple[str, str]:
    if deadline is None:
        return "", ""
    left = deadline - now
    if left < timedelta(0):
        return f"просрочен на {duration(-left)}", "late"
    return f"осталось {duration(left)}", "soon" if left < SOON else "ok"


def courier_collects(order: Order) -> str:
    """Оплата при получении: сколько курьер берёт с покупателя — пока заказ не доставлен."""
    if order.payment_method != Order.PaymentMethod.COD or order.status not in (S.COD, S.PICKING, S.HANDED_TO_CARRIER):
        return ""
    return f"При получении: взять {money(order.total_uzs)} сум"


def refund_way(order: Order) -> str:
    return "наличными или переводом" if order.payment_method == Order.PaymentMethod.COD else "в кабинете Payme / Click"


def _notes(order: Order) -> list[str]:
    notes = [
        f"{request.supplier.name}: {request.get_status_display().lower()}"
        + (f" ${request.proposed_cost_usd}" if request.proposed_cost_usd else "")
        for request in order.supplier_requests.all()
    ]
    shipment = getattr(order, "shipment", None) if order.status == S.HANDED_TO_CARRIER else None
    if shipment:
        notes.append(shipment.courier_name and f"{shipment.courier_name}, {shipment.courier_phone}"
                     or f"{shipment.service_name}, накладная {shipment.tracking}")
    if collect := courier_collects(order):
        notes.append(collect)
    return notes


def sections(now: datetime) -> list[dict]:
    paid_at = OrderEvent.objects.filter(order=OuterRef("pk"), status_to__in=PICKABLE).order_by("-created_at")
    result = []
    for key, title, statuses, deadline_field, action in STAGES:
        orders = (
            Order.objects.filter(status__in=statuses)
            .select_related("customer", "shipment")
            .prefetch_related("lines__variant__product_model", "supplier_requests__supplier")
            .annotate(paid_at=Subquery(paid_at.values("created_at")[:1]))
            .order_by("created_at")
        )
        rows = []
        for order in orders:
            if deadline_field == "pick_deadline":
                deadline = order.paid_at + PICK_WITHIN if order.paid_at else None
            else:
                deadline = getattr(order, deadline_field) if deadline_field else None
            text, css = timer(deadline, now)
            rows.append({
                "order": order,
                "summary": ", ".join(
                    f"{line.variant.product_model.name_ru} × {line.qty}" for line in order.lines.all() if not line.is_gift
                ),
                "total": f"{order.total_uzs:,}".replace(",", " "),
                "notes": _notes(order),
                "timer": text,
                "timer_class": css,
                "deadline": deadline,
                "action": action,
            })
        rows.sort(key=lambda row: row["deadline"] or row["order"].created_at)
        result.append({"key": key, "title": title, "rows": rows})
    return result


def find_orders(query: str) -> list[Order]:
    """Поиск для оператора: номер заказа целиком или телефон покупателя (хватит последних 7–9 цифр)."""
    digits = re.sub(r"\D", "", query)
    condition = Q(number__iexact=query.strip())
    if len(digits) >= 7:
        condition |= Q(customer__phone__endswith=digits[-9:])
    return list(Order.objects.filter(condition).select_related("customer").order_by("-created_at")[:20])


def pick_context(order: Order, now: datetime) -> dict:
    lines = []
    for line in order.lines.select_related("variant__product_model__category").order_by("pk"):
        units = list(line.units.order_by("pk"))
        lines.append({
            "line": line,
            "label": variant_title(line.variant),
            "serialized": line.variant.product_model.category.is_serialized,
            "units": units,
            "missing": max(line.qty - len(units), 0),
        })
    return {
        "order": order,
        "lines": lines,
        "total": f"{order.total_uzs:,}".replace(",", " "),
        # Курсор сразу в первое поле IMEI — сканер «печатает» код и нажимает Enter.
        "focus_line": next((item["line"].pk for item in lines if item["serialized"] and item["missing"]), None),
        "problems": picking_problems(order) if order.status == S.PICKING else [],
        "shipment": getattr(order, "shipment", None),
        "can_start": order.status in PICKABLE,
        "can_confirm": order.status == S.SOURCING,
        "picking": order.status == S.PICKING,
        "handed": order.status == S.HANDED_TO_CARRIER,
        "can_cancel": order.status in CANCELLABLE,
        "paid": order.payment_method != Order.PaymentMethod.COD
        and order.status not in (S.SOURCING, S.CONFIRMED, S.AWAITING_PAYMENT),
        "collect": courier_collects(order),
        "refund_way": refund_way(order),
        "events": [
            {"at": event.created_at, "status": S(event.status_to).label, "note": event.note}
            for event in order.events.order_by("-created_at", "-pk")[:10]
        ],
        "Z": InventoryUnit.UzimeiStatus,
        **_return_context(order, now),
    }


def _return_context(order: Order, now: datetime) -> dict:
    deadline = return_deadline(order)
    request = ReturnRequest.objects.filter(order=order).first()
    return {
        "can_return": order.status in (S.DELIVERED, S.COMPLETED) and deadline is not None and now <= deadline,
        "return_deadline": deadline,
        "return_request": request,
        "return_refund": money(request.refund_amount_uzs) if request and request.refund_amount_uzs is not None else "",
        "returning": order.status == S.RETURN_REQUESTED,
        "inspected": order.status == S.INSPECTED,
    }


def _pk(value: str | None) -> int:
    if not value or not (value.isascii() and value.isdigit()):
        raise Http404
    return int(value)


def _line(order: Order, value: str | None) -> OrderLine:
    line = OrderLine.objects.filter(order=order, pk=_pk(value)).first()
    if line is None:
        raise Http404
    return line


def _unit(order: Order, value: str | None) -> InventoryUnit:
    unit = InventoryUnit.objects.filter(order_line__order=order, pk=_pk(value)).first()
    if unit is None:
        raise Http404
    return unit


def _amount(value: str | None) -> int:
    value = (value or "").replace(" ", "")
    return int(value) if value.isascii() and value.isdigit() and len(value) <= 12 else 0


def perform(order: Order, action: str, data, now: datetime, actor: str) -> tuple[str, str]:
    """Действие оператора. Возвращает (сообщение, куда вернуться: desk | pick); ошибка — OrderError."""
    if action == "confirm":
        confirm_sourcing(order, now, actor)
        return "Подтверждено у поставщика — покупатель может оплачивать", "desk"
    if action == "start":
        start_picking(order, now, actor)
        return "Сборка начата", "pick"
    if action == "add_unit":
        unit = add_unit(_line(order, data.get("line")), data.get("imei", ""), now, actor,
                        uzimei_registered=data.get("uzimei") == "on")
        return f"IMEI {unit.imei1} добавлен", "pick"
    if action == "remove_unit":
        remove_unit(_unit(order, data.get("unit")), now, actor)
        return "Устройство убрано из заказа", "pick"
    if action == "uzimei":
        mark_uzimei(_unit(order, data.get("unit")), data.get("registered") == "yes", now, actor)
        return "Отметка UzIMEI сохранена", "pick"
    if action == "ship":
        handover = Handover(
            courier_name=data.get("courier_name", ""), courier_phone=data.get("courier_phone", ""),
            service_name=data.get("service_name", ""), tracking=data.get("tracking", ""),
            cost_uzs=_amount(data.get("cost_uzs")),
        )
        ship(order, data.get("carrier", ""), handover, now, actor)
        return f"Заказ {order.number} передан в доставку", "desk"
    if action == "deliver":
        deliver(order, now, actor)
        return f"Заказ {order.number} доставлен", "desk"
    if action == "return_open":
        open_return(order, data.get("reason", ""), now, actor)
        return "Возврат оформлен — ждём товар", "pick"
    if action == "return_inspect":
        imeis = re.split(r"[\s,;]+", data.get("imeis", ""))
        request = inspect_return(order, imeis, data.get("gift_returned") == "on", now, actor)
        if request.status == ReturnRequest.Status.REJECTED:
            return "IMEI не совпадает с проданными — возврат отклонён", "pick"
        return f"Возврат принят. Верните покупателю {money(request.refund_amount_uzs)} сум {refund_way(order)}", "pick"
    if action == "return_reject":
        reject_return(order, data.get("note", ""), now, actor)
        return "Возврат отклонён", "pick"
    if action == "return_refund":
        refund_return(order, now, actor)
        return f"Заказ {order.number}: деньги возвращены", "pick"
    if action == "cancel":
        cancel_order(order, now, actor, "Отменён оператором")
        return f"Заказ {order.number} отменён", "desk"
    raise Http404
