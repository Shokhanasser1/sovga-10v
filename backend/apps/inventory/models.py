from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Variant
from apps.sourcing.models import Supplier, Warehouse

from .imei import validate_imei


class PurchaseBatch(models.Model):
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="поставщик")
    received_at = models.DateTimeField(default=timezone.now, verbose_name="получена")
    note = models.CharField(max_length=200, blank=True, verbose_name="заметка")

    class Meta:
        verbose_name = "партия закупки"
        verbose_name_plural = "партии закупки"

    def __str__(self) -> str:
        return f"Партия {self.pk} от {self.received_at:%Y-%m-%d}"


class InventoryUnit(models.Model):
    class UzimeiStatus(models.TextChoices):
        UNKNOWN = "unknown", "Не проверен"
        REGISTERED = "registered", "Зарегистрирован"
        NOT_REGISTERED = "not_registered", "Не зарегистрирован"

    class State(models.TextChoices):
        IN_STOCK = "in_stock", "На складе"
        RESERVED = "reserved", "Собран под заказ"
        SOLD = "sold", "Продан"
        RETURNED = "returned", "Возвращён"
        DEFECTIVE = "defective", "Брак"

    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, related_name="units", verbose_name="вариант товара")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="units", verbose_name="склад")
    imei1 = models.CharField(max_length=15, blank=True, validators=[validate_imei], verbose_name="IMEI 1")
    imei2 = models.CharField(max_length=15, blank=True, validators=[validate_imei], verbose_name="IMEI 2")
    serial = models.CharField(max_length=64, blank=True, verbose_name="серийный номер")
    uzimei_status = models.CharField(
        max_length=15, choices=UzimeiStatus.choices, default=UzimeiStatus.UNKNOWN, verbose_name="UzIMEI"
    )
    purchase_batch = models.ForeignKey(
        PurchaseBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="units",
        verbose_name="партия закупки"
    )
    cost_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="себестоимость, $")
    status = models.CharField(max_length=10, choices=State.choices, default=State.IN_STOCK, verbose_name="статус")
    order_line = models.ForeignKey(
        "orders.OrderLine", null=True, blank=True, on_delete=models.SET_NULL, related_name="units",
        help_text="Строка заказа, под которую собрано или продано устройство", verbose_name="строка заказа",
    )
    received_for_order = models.BooleanField(
        default=False, help_text="Принято от поставщика под заказ: при отмене заказа не возвращается на склад",
        verbose_name="принят под заказ"
    )
    received_at = models.DateTimeField(auto_now_add=True, verbose_name="принят")

    class Meta:
        verbose_name = "устройство на складе"
        verbose_name_plural = "устройства на складе"
        constraints = [
            models.UniqueConstraint(
                fields=["imei1"],
                condition=~Q(imei1=""),
                name="unique_imei1",
                violation_error_message="Устройство с таким IMEI уже есть",
            )
        ]

    def __str__(self) -> str:
        return f"{self.variant} — {self.imei1 or self.serial}"

    def clean(self) -> None:
        errors = {}
        if self.variant_id and not self.variant.product_model.category.is_serialized:
            errors["variant"] = "Эта категория не ведётся поштучно"
        if not self.imei1 and not self.serial:
            errors["imei1"] = "Укажите IMEI или серийный номер"
        if self.imei2 and self.imei2 == self.imei1:
            errors["imei2"] = "IMEI2 совпадает с IMEI1"
        if errors:
            raise ValidationError(errors)
