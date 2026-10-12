from django.db import models

from apps.catalog.models import Variant
from apps.customers.models import Customer
from apps.sourcing.models import Offer, Reservation, Supplier


class Order(models.Model):
    class Status(models.TextChoices):
        SOURCING = "sourcing", "Ждёт подтверждения поставщика"
        CONFIRMED = "confirmed", "Ждёт оплаты"
        AWAITING_PAYMENT = "awaiting_payment", "Оплата начата"
        PAID = "paid", "Оплачен"
        INSTALLMENT_PENDING = "installment_pending", "Оформляется рассрочка"
        SIGNED = "signed", "Рассрочка оформлена"
        COD = "cod", "Оплата при получении"
        PICKING = "picking", "Собирается"
        HANDED_TO_CARRIER = "handed_to_carrier", "Передан в доставку"
        DELIVERED = "delivered", "Доставлен"
        COMPLETED = "completed", "Завершён"
        CANCELLED = "cancelled", "Отменён"
        RETURN_REQUESTED = "return_requested", "Запрошен возврат"
        INSPECTED = "inspected", "Возврат проверен"
        REFUNDED = "refunded", "Деньги возвращены"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Картой онлайн"
        INSTALLMENT = "installment", "Рассрочка"
        COD = "cod", "При получении"

    number = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="номер")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders", verbose_name="покупатель")
    status = models.CharField(max_length=20, choices=Status.choices, verbose_name="статус")
    payment_method = models.CharField(
        max_length=12, choices=PaymentMethod.choices, default=PaymentMethod.CARD, verbose_name="оплата"
    )
    address_text = models.CharField(max_length=300, verbose_name="адрес")
    address_landmark = models.CharField(max_length=200, blank=True, verbose_name="ориентир")
    comment = models.CharField(max_length=500, blank=True, verbose_name="комментарий")
    total_uzs = models.PositiveBigIntegerField(verbose_name="сумма, сум")
    rate = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Курс с учётом спреда на момент заказа", verbose_name="курс"
    )
    price_lock_until = models.DateTimeField(
        help_text="До этого времени цена зафиксирована", verbose_name="цена закреплена до"
    )
    sla_deadline = models.DateTimeField(
        null=True, blank=True, help_text="Срок ответа поставщика", verbose_name="срок поставщика"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="изменён")

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ["-created_at", "-pk"]

    def __str__(self) -> str:
        return self.number or f"заказ #{self.pk}"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines", verbose_name="заказ")
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, verbose_name="вариант товара")
    qty = models.PositiveSmallIntegerField(verbose_name="количество")
    price_uzs = models.PositiveBigIntegerField(help_text="За единицу; у подарка — 0", verbose_name="цена, сум")
    cost_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="себестоимость, $")
    offer = models.ForeignKey(Offer, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="предложение")
    reservation = models.ForeignKey(
        Reservation, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="резерв"
    )
    is_gift = models.BooleanField(default=False, verbose_name="подарок")
    gift_value_uzs = models.PositiveBigIntegerField(
        default=0, help_text="У подарка — его цена за штуку на момент заказа: удерживается, если подарок не вернули",
        verbose_name="цена подарка, сум"
    )
    gift_for = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="gifts", verbose_name="подарок к строке"
    )

    class Meta:
        verbose_name = "строка заказа"
        verbose_name_plural = "строки заказа"
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.variant} × {self.qty}"


class OrderEvent(models.Model):
    """История заказа: каждый переход статуса с автором и пояснением."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events", verbose_name="заказ")
    status_from = models.CharField(max_length=20, blank=True, verbose_name="был статус")
    status_to = models.CharField(max_length=20, verbose_name="стал статус")
    actor = models.CharField(max_length=60, verbose_name="кто")
    note = models.CharField(max_length=300, blank=True, verbose_name="заметка")
    created_at = models.DateTimeField(verbose_name="создан")

    class Meta:
        verbose_name = "событие заказа"
        verbose_name_plural = "история заказов"
        ordering = ["created_at", "pk"]

    def __str__(self) -> str:
        return f"{self.order}: {self.status_from or '—'} → {self.status_to}"


class SupplierRequest(models.Model):
    """Запрос поставщику «есть ли товар» по заказу. Отвечает поставщик кнопками в боте или менеджер в админке."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ждём ответа"
        CONFIRMED = "confirmed", "Есть"
        DECLINED = "declined", "Нет в наличии"
        AWAITING_PRICE = "awaiting_price", "Пишет новую цену"
        PRICE_OFFERED = "price_offered", "Предложил другую цену"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="supplier_requests", verbose_name="заказ")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="requests", verbose_name="поставщик")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name="статус")
    proposed_cost_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="предложенная цена, $"
    )
    message_id = models.BigIntegerField(null=True, blank=True, verbose_name="сообщение в Telegram")
    created_at = models.DateTimeField(verbose_name="создан")
    sent_at = models.DateTimeField(
        null=True, blank=True, help_text="Пусто — поставщик без бота, подтверждает менеджер", verbose_name="отправлен"
    )
    answered_at = models.DateTimeField(null=True, blank=True, verbose_name="ответ")
    alerted_at = models.DateTimeField(
        null=True, blank=True, help_text="Когда менеджерам сообщили, что поставщик молчит",
        verbose_name="менеджеры предупреждены",
    )

    class Meta:
        verbose_name = "запрос поставщику"
        verbose_name_plural = "запросы поставщикам"
        constraints = [models.UniqueConstraint(fields=["order", "supplier"], name="unique_supplier_request")]

    def __str__(self) -> str:
        return f"{self.order} → {self.supplier}"


class OperatorDesk(Order):
    """Пункт меню админки «Рабочее место оператора» — своей таблицы нет."""

    class Meta:
        proxy = True
        verbose_name = "рабочее место оператора"
        verbose_name_plural = "рабочее место оператора"


class ReturnRequest(models.Model):
    """Возврат доставленного заказа: приёмка со сверкой IMEI, затем возврат денег."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Ждём товар"
        ACCEPTED = "accepted", "Принят — вернуть деньги"
        REJECTED = "rejected", "Отказ"
        REFUNDED = "refunded", "Деньги возвращены"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="returns", verbose_name="заказ")
    reason = models.CharField(max_length=300, verbose_name="причина")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED, verbose_name="статус")
    imeis_received = models.JSONField(default=list, blank=True, verbose_name="принятые IMEI")
    gift_returned = models.BooleanField(null=True, blank=True, verbose_name="подарок вернули")
    refund_amount_uzs = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="к возврату, сум")
    note = models.CharField(max_length=300, blank=True, verbose_name="заметка")
    created_at = models.DateTimeField(verbose_name="создан")
    inspected_at = models.DateTimeField(null=True, blank=True, verbose_name="проверен")
    refunded_at = models.DateTimeField(null=True, blank=True, verbose_name="деньги возвращены")

    class Meta:
        verbose_name = "возврат"
        verbose_name_plural = "возвраты"
        ordering = ["-pk"]

    def __str__(self) -> str:
        return f"Возврат {self.order}"


class SalesReport(Order):
    """Пункт меню админки «Выгрузка для бухгалтера» — своей таблицы нет."""

    class Meta:
        proxy = True
        verbose_name = "выгрузка для бухгалтера"
        verbose_name_plural = "выгрузка для бухгалтера"
