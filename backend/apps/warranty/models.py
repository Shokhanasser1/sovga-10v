from django.db import models


class WarrantyCase(models.Model):
    """Гарантийный случай по проданному устройству."""

    class Status(models.TextChoices):
        OPEN = "open", "Принят от покупателя"
        IN_SERVICE = "in_service", "В сервисном центре"
        READY = "ready", "Готов — выдать покупателю"
        CLOSED = "closed", "Выдан покупателю"
        REJECTED = "rejected", "Отказ: не гарантийный случай"

    unit = models.ForeignKey("inventory.InventoryUnit", on_delete=models.PROTECT, related_name="warranty_cases")
    complaint = models.CharField(max_length=500, help_text="Что не так со слов покупателя")
    service_center = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    note = models.TextField(blank=True, help_text="Что сделали: ремонт, замена, причина отказа")
    opened_at = models.DateTimeField()
    opened_by = models.CharField(max_length=100)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        verbose_name = "гарантийный случай"
        verbose_name_plural = "гарантийные случаи"

    def __str__(self) -> str:
        return f"Гарантия {self.unit.imei1 or self.unit.serial}"


CLOSED_STATUSES = {WarrantyCase.Status.CLOSED, WarrantyCase.Status.REJECTED}
