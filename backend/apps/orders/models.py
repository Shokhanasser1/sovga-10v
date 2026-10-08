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

    number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices)
    payment_method = models.CharField(max_length=12, choices=PaymentMethod.choices, default=PaymentMethod.CARD)
    address_text = models.CharField(max_length=300)
    address_landmark = models.CharField(max_length=200, blank=True)
    comment = models.CharField(max_length=500, blank=True)
    total_uzs = models.PositiveBigIntegerField()
    rate = models.DecimalField(max_digits=12, decimal_places=2, help_text="Курс с учётом спреда на момент заказа")
    price_lock_until = models.DateTimeField(help_text="До этого времени цена зафиксирована")
    sla_deadline = models.DateTimeField(null=True, blank=True, help_text="Срок ответа поставщика")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self) -> str:
        return self.number or f"заказ #{self.pk}"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT)
    qty = models.PositiveSmallIntegerField()
    price_uzs = models.PositiveBigIntegerField(help_text="За единицу; у подарка — 0")
    cost_usd = models.DecimalField(max_digits=12, decimal_places=2)
    offer = models.ForeignKey(Offer, null=True, blank=True, on_delete=models.SET_NULL)
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.SET_NULL)
    is_gift = models.BooleanField(default=False)
    gift_for = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="gifts"
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.variant} × {self.qty}"


class OrderEvent(models.Model):
    """История заказа: каждый переход статуса с автором и пояснением."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    status_from = models.CharField(max_length=20, blank=True)
    status_to = models.CharField(max_length=20)
    actor = models.CharField(max_length=60)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField()

    class Meta:
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

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="supplier_requests")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="requests")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    proposed_cost_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    message_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Пусто — поставщик без бота, подтверждает менеджер")
    answered_at = models.DateTimeField(null=True, blank=True)
    alerted_at = models.DateTimeField(null=True, blank=True, help_text="Когда менеджерам сообщили, что поставщик молчит")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order", "supplier"], name="unique_supplier_request")]

    def __str__(self) -> str:
        return f"{self.order} → {self.supplier}"


class OperatorDesk(Order):
    """Пункт меню админки «Рабочее место оператора» — своей таблицы нет."""

    class Meta:
        proxy = True
        verbose_name = "рабочее место оператора"
        verbose_name_plural = "рабочее место оператора"
