from django.db import models

from apps.orders.models import Order


class Payment(models.Model):
    """Одна транзакция платёжного провайдера по заказу."""

    class Provider(models.TextChoices):
        PAYME = "payme", "Payme"
        CLICK = "click", "Click"

    class State(models.TextChoices):
        CREATED = "created", "Создан, ждёт проведения"
        PAID = "paid", "Проведён"
        CANCELLED = "cancelled", "Отменён до проведения"
        REFUNDED = "refunded", "Отменён после проведения (возврат)"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments", verbose_name="заказ")
    provider = models.CharField(max_length=10, choices=Provider.choices, verbose_name="провайдер")
    external_id = models.CharField(
        max_length=64, help_text="ID транзакции у провайдера", verbose_name="номер у провайдера"
    )
    amount_uzs = models.PositiveBigIntegerField(verbose_name="сумма, сум")
    state = models.CharField(max_length=10, choices=State.choices, default=State.CREATED, verbose_name="состояние")
    provider_time = models.BigIntegerField(
        null=True, blank=True, help_text="Время у провайдера, мс", verbose_name="время у провайдера"
    )
    created_at = models.DateTimeField(verbose_name="создан")
    performed_at = models.DateTimeField(null=True, blank=True, verbose_name="проведён")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="отменён")
    cancel_reason = models.SmallIntegerField(null=True, blank=True, verbose_name="причина отмены")
    raw = models.JSONField(default=dict, blank=True, verbose_name="исходные данные")

    class Meta:
        verbose_name = "платёж"
        verbose_name_plural = "платежи"
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "external_id"], name="unique_provider_transaction")
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} {self.external_id}"
