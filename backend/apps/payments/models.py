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

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    external_id = models.CharField(max_length=64, help_text="ID транзакции у провайдера")
    amount_uzs = models.PositiveBigIntegerField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.CREATED)
    provider_time = models.BigIntegerField(null=True, blank=True, help_text="Время у провайдера, мс")
    created_at = models.DateTimeField()
    performed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.SmallIntegerField(null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "external_id"], name="unique_provider_transaction")
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} {self.external_id}"
