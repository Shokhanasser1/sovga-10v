from django.db import models

from apps.customers.models import Customer
from apps.sourcing.models import Supplier


class TelegramLink(models.Model):
    """Одноразовый код привязки чата. Приходит боту как /start <вид>_<код>."""

    class Kind(models.TextChoices):
        CUSTOMER = "c", "Покупатель"
        SUPPLIER = "s", "Поставщик"

    code = models.CharField(max_length=32, unique=True)
    kind = models.CharField(max_length=1, choices=Kind.choices)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.customer or self.supplier}"
