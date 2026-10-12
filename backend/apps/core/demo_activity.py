"""История учебного магазина для seed_demo: покупатели и заказы во всех статусах за полтора месяца.

Каждый шаг — настоящий сервис магазина с `now` в прошлом: оформление, ответ поставщика в боте, учебная оплата
Payme / Click, сборка по IMEI, отгрузка, доставка, возврат, гарантия. Ни один статус не записан в обход машины
состояний, поэтому история в админке, отчёте и «Имитации Telegram» такая же, как после настоящей работы.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.bot import demo as demo_chats
from apps.customers.models import Customer
from apps.customers.services import customer_for_phone
from apps.delivery.carriers import Handover
from apps.delivery.models import Shipment
from apps.inventory.imei import with_check_digit
from apps.inventory.models import InventoryUnit
from apps.notifications import telegram
from apps.notifications.outbox import deliver_pending
from apps.orders.fulfilment import add_unit, deliver, ship, start_picking
from apps.orders.models import Order
from apps.orders.quote import CartItem, quote
from apps.orders.returns import complete_delivered, inspect_return, open_return, refund_return
from apps.orders.services import DeliveryAddress, cancel_order, create_order
from apps.orders.supplier_requests import answer_request
from apps.payments.demo import simulate_click, simulate_payme
from apps.sourcing.models import Supplier
from apps.warranty.models import WarrantyCase
from apps.warranty.services import open_case

S = Order.Status
OPERATOR = "operator:demo"


@dataclass(frozen=True)
class DemoCustomer:
    phone: str
    name: str
    language: str
    address: str
    landmark: str
    city: str = "Ташкент"


CUSTOMERS = [
    DemoCustomer("+998901110101", "Азиз Каримов", "ru", "Ташкент, Юнусабад 11-квартал, дом 15, кв. 24",
                 "рядом с метро «Юнусабад»"),
    DemoCustomer("+998901110102", "Dilnoza Rahimova", "uz", "Toshkent, Chilonzor 9-mavze, 12-uy, 8-xonadon",
                 "Chilonzor bozori yonida"),
    DemoCustomer("+998901110103", "Шахзод Турсунов", "ru", "Самарканд, ул. Регистанская, 41", "напротив школы №21",
                 "Самарканд"),
    DemoCustomer("+998901110104", "Malika Yusupova", "uz", "Buxoro, Mustaqillik koʻchasi, 7-uy", "Ark yonida",
                 "Бухара"),
    DemoCustomer("+998901110105", "Тимур Ахмедов", "ru", "Ташкент, Мирабадский район, ул. Тараса Шевченко, 22",
                 "бизнес-центр, 3 этаж"),
    DemoCustomer("+998901110106", "Jasur Islomov", "uz", "Namangan, Navoiy koʻchasi, 18-uy", "", "Наманган"),
    DemoCustomer("+998901110107", "Нигора Абдуллаева", "ru", "Фергана, ул. Ал-Фаргоний, 5, кв. 3",
                 "за торговым центром", "Фергана"),
    DemoCustomer("+998901110108", "Sardor Qodirov", "uz", "Andijon, Bobur shoh koʻchasi, 30-uy", "", "Андижан"),
    DemoCustomer("+998901110109", "Елена Ким", "ru", "Ташкент, Мирзо-Улугбек, массив Буюк Ипак Йули, 40, кв. 61",
                 "второй подъезд"),
    DemoCustomer("+998901110110", "Bekzod Ergashev", "uz", "Qarshi, Islom Karimov koʻchasi, 101-uy", "", "Карши"),
    DemoCustomer("+998901110111", "Камила Назарова", "ru", "Ташкент, Сергели-8, дом 3, кв. 12",
                 "домофон не работает — позвоните"),
    DemoCustomer("+998901110112", "Otabek Mirzayev", "uz", "Nukus, Doʻstlik guzari, 14-uy", "", "Нукус"),
]
# Двое покупателей не подключили бота — им приходят только SMS
WITHOUT_TELEGRAM = {"+998901110106", "+998901110110"}


@dataclass(frozen=True)
class Story:
    customer: int
    days_ago: float
    items: tuple[tuple[str, int], ...]
    provider: str
    stage: str
    comment: str = ""
    return_reason: str = ""


# Этапы: sourcing (ждёт поставщика), declined (поставщик отказал), confirmed (ждёт оплаты),
# cancelled (покупатель отменил), paid, refunded_unshipped (деньги вернули до отгрузки), picking, shipped,
# delivered, return_requested, inspected, refunded (возврат завершён), completed.
STORIES = [
    Story(0, 44, (("IP17P-256-ORG", 1),), "payme", "completed", "Позвоните за час до доставки"),
    Story(1, 42, (("A56-128-BLK", 1),), "click", "completed"),
    Story(2, 40, (("RN14-256-BLK", 1),), "payme", "completed"),
    Story(3, 38, (("S25U-256-BLK", 1),), "payme", "completed"),
    Story(4, 36, (("AIRPODS-PRO-3", 1), ("CHG-APPLE-20", 1)), "click", "completed"),
    Story(5, 35, (("IP17-256-BLK", 1),), "payme", "refunded", return_reason="Не подошёл — хочу модель поменьше"),
    Story(6, 33, (("IPAD11-128-BLU", 1),), "click", "completed", "Подарок дочке, упакуйте, пожалуйста"),
    Story(7, 31, (("X15-256-BLK", 1),), "payme", "completed"),
    Story(8, 30, (("GW8-44-SLV", 1), ("XM6-BLK", 1)), "payme", "completed"),
    Story(9, 28, (("R14C-128-BLK", 2),), "click", "completed", "Два телефона — для родителей"),
    Story(10, 27, (("IP16E-128-BLK", 1),), "payme", "cancelled"),
    Story(11, 25, (("S25E-256-SLV", 1),), "payme", "declined"),
    Story(0, 24, (("CASE-IP17P-CLR", 1), ("GLS-IP17P", 1)), "click", "completed"),
    Story(1, 22, (("A36-128-BLK", 1),), "payme", "completed"),
    Story(2, 20, (("IP17PM-256-ORG", 1),), "payme", "refunded_unshipped"),
    Story(3, 18, (("H400-256-BLK", 1),), "click", "completed"),
    Story(4, 16, (("S25-256-BLU", 1),), "payme", "completed"),
    Story(5, 14, (("JBL520-BLU", 1), ("PB-XIAOMI-20K", 1)), "click", "completed"),
    Story(6, 9, (("IP17P-256-BLU", 1),), "payme", "inspected", return_reason="Не понравился цвет"),
    Story(7, 8, (("AW11-46-BLK", 1),), "click", "delivered"),
    Story(8, 6, (("IP16-128-BLK", 1),), "payme", "return_requested",
          return_reason="Купили в подарок, а у именинника уже есть такой"),
    Story(9, 5, (("TABS10FE-128-GRY", 1),), "payme", "delivered"),
    Story(10, 3, (("IP17P-256-ORG", 1),), "click", "delivered"),
    Story(11, 2, (("RN14-256-BLK", 1),), "payme", "shipped"),
    Story(0, 1, (("IP17-256-BLK", 1),), "payme", "picking"),
    Story(1, 0.15, (("A56-128-BLK", 1),), "click", "paid"),
    Story(2, 0.01, (("XWS4-47-BLK", 1),), "click", "confirmed"),
    Story(3, 0.005, (("ZFLIP7-256-BLU", 1),), "payme", "sourcing", "Можно ли доставить сегодня?"),
]
# Гарантийные случаи: номер истории, через сколько дней после доставки, жалоба, сервисный центр, в сервисе ли
WARRANTY = [
    (0, 33, "Не заряжается от кабеля, только по MagSafe", "Сервисный центр iStore, Ташкент", True),
    (9, 20, "Перестала работать фронтальная камера", "Xiaomi сервис, Ташкент", False),
]
STOP = {
    "sourcing": 0, "declined": 0, "confirmed": 1, "cancelled": 1, "paid": 2, "refunded_unshipped": 2, "picking": 3,
    "shipped": 4, "delivered": 5, "completed": 5, "return_requested": 6, "inspected": 7, "refunded": 8,
}
COURIER = Handover(courier_name="Улугбек", courier_phone="+998935550101")


def _moment(now: datetime, days_ago: float, index: int) -> datetime:
    """Утро или день нужного дня по Ташкенту; свежие истории — просто столько-то часов назад."""
    if days_ago < 1:
        return now - timedelta(days=days_ago)
    day = timezone.localtime(now - timedelta(days=days_ago))
    return day.replace(hour=10 + index % 8, minute=(index * 17) % 60, second=0, microsecond=0)


def _customer(row: DemoCustomer) -> Customer:
    customer = customer_for_phone(row.phone)
    customer.name, customer.language = row.name, row.language
    if row.phone not in WITHOUT_TELEGRAM:
        customer.telegram_chat_id = demo_chats.customer_chat(customer)
    customer.save()
    return customer


def _items(story: Story, now: datetime) -> list[CartItem]:
    """Подарок — первый из предложенных, как выбирает корзина."""
    items = []
    for sku, qty in story.items:
        line = quote([CartItem(sku, qty)], Order.PaymentMethod.CARD, now).lines[0]
        items.append(CartItem(sku, qty, line.gift_options[0].sku if line.gift_options else None))
    return items


def _pay(order: Order, provider: str, now: datetime) -> None:
    error = (simulate_payme if provider == "payme" else simulate_click)(order, "pay", now)
    if error:
        raise RuntimeError(f"{order.number}: учебная оплата не прошла — {error}")


def _scan(order: Order, now: datetime) -> list[str]:
    """Сборка: со своего склада — устройства с полки, у поставщика — новые IMEI. Возвращает IMEI заказа."""
    imeis = []
    for line in order.lines.select_related("variant__product_model__category", "offer").order_by("pk"):
        if line.is_gift or not line.variant.product_model.category.is_serialized:
            continue
        for number in range(line.qty):
            if line.offer and line.offer.is_own:
                unit = InventoryUnit.objects.filter(
                    variant=line.variant, status=InventoryUnit.State.IN_STOCK, order_line__isnull=True
                ).order_by("pk").first()
                imei = unit.imei1
            else:
                imei = with_check_digit(f"86{order.pk:06d}{line.pk:04d}{number:02d}"[:14])
            add_unit(line, imei, now, OPERATOR, uzimei_registered=True)
            imeis.append(imei)
    return imeis


def _handover(row: DemoCustomer, order: Order) -> tuple[str, Handover]:
    if row.city == "Ташкент":
        return Shipment.Carrier.OWN, COURIER
    return Shipment.Carrier.SERVICE, Handover(service_name="BTS", tracking=f"BTS-{order.pk:07d}")


def _play(story: Story, index: int, customers: list[Customer], now: datetime) -> Order:
    row, customer = CUSTOMERS[story.customer], customers[story.customer]
    moment = _moment(now, story.days_ago, index)
    order = create_order(customer, _items(story, moment), Order.PaymentMethod.CARD,
                         DeliveryAddress(row.address, row.landmark), story.comment, moment)
    Order.objects.filter(pk=order.pk).update(created_at=moment)
    if order.status == S.SOURCING:
        if story.stage == "sourcing":
            return order
        moment += timedelta(minutes=25)
        request = order.supplier_requests.select_related("supplier").first()
        choice = "no" if story.stage == "declined" else "yes"
        answer_request(request.pk, request.supplier.telegram_chat_id, choice, moment)
    stop = STOP[story.stage]
    if stop < 1:
        return order
    if story.stage == "cancelled":
        cancel_order(order, moment + timedelta(minutes=10), f"customer:{customer.phone}", "Передумал", by_customer=True)
        return order
    if stop < 2:
        return order
    moment += timedelta(minutes=10)
    _pay(order, story.provider, moment)
    if story.stage == "refunded_unshipped":
        simulate_payme(order, "refund", moment + timedelta(hours=3))
        return order
    if stop < 3:
        return order
    moment += timedelta(hours=2)
    start_picking(order, moment, OPERATOR)
    if stop < 4:
        return order
    imeis = _scan(order, moment + timedelta(minutes=15))
    carrier, handover = _handover(row, order)
    ship(order, carrier, handover, moment + timedelta(hours=2), OPERATOR)
    if stop < 5:
        return order
    delivered = moment + timedelta(days=1)
    deliver(order, delivered, "courier")
    if story.stage == "completed":
        complete_delivered(delivered + timedelta(days=settings.RETURN_DAYS, hours=1))
    if stop < 6:
        return order
    returned = delivered + timedelta(days=2)
    open_return(order, story.return_reason, returned, f"customer:{customer.phone}")
    if stop < 7:
        return order
    inspect_return(order, imeis, True, returned + timedelta(days=1), OPERATOR)
    if stop < 8:
        return order
    refund_return(order, returned + timedelta(days=1, hours=2), OPERATOR)
    return order


def _warranty(orders: list[Order], now: datetime) -> None:
    for index, days, complaint, center, in_service in WARRANTY:
        order = orders[index]
        unit = InventoryUnit.objects.filter(order_line__order=order).order_by("pk").first()
        delivered = Shipment.objects.get(order=order).delivered_at
        case = open_case(unit, complaint, center, min(delivered + timedelta(days=days), now), OPERATOR)
        if in_service:
            case.status, case.note = WarrantyCase.Status.IN_SERVICE, "Отправлен в сервисный центр, ждём диагностику"
            case.save(update_fields=["status", "note"])


def _deliver_events(now: datetime) -> None:
    """Учебный режим без токена: события сразу попадают в «Имитацию Telegram»."""
    if not telegram.simulated():
        return
    for _ in range(100):
        result = deliver_pending(now)
        if not (result.done or result.retried or result.failed):
            return


def create_history(now: datetime) -> int:
    """Создаёт историю один раз — пока учебных покупателей нет. Возвращает число заказов."""
    if Customer.objects.filter(phone__in=[row.phone for row in CUSTOMERS]).exists():
        return 0
    for supplier in Supplier.objects.filter(telegram_chat_id__isnull=True):
        supplier.telegram_chat_id = demo_chats.supplier_chat(supplier)
        supplier.save(update_fields=["telegram_chat_id"])
    customers = [_customer(row) for row in CUSTOMERS]
    orders = [_play(story, index, customers, now) for index, story in enumerate(STORIES)]
    for customer in customers:
        first = customer.orders.order_by("created_at").first()
        if first:
            Customer.objects.filter(pk=customer.pk).update(created_at=first.created_at - timedelta(hours=1))
    _warranty(orders, now)
    _deliver_events(now)
    return len(orders)
