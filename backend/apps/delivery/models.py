from django.db import models


class Shipment(models.Model):
    """Передача заказа в доставку: свой курьер или служба доставки."""

    class Carrier(models.TextChoices):
        OWN = "own", "Свой курьер"
        SERVICE = "service", "Служба доставки"

    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="shipment")
    carrier = models.CharField(max_length=20, choices=Carrier.choices)
    courier_name = models.CharField(max_length=100, blank=True)
    courier_phone = models.CharField(max_length=13, blank=True)
    service_name = models.CharField(max_length=100, blank=True)
    tracking = models.CharField(max_length=64, blank=True, help_text="Номер накладной службы доставки")
    cost_uzs = models.PositiveBigIntegerField(default=0, help_text="Сколько доставка стоила магазину")
    handed_at = models.DateTimeField()
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "доставка"
        verbose_name_plural = "доставки"

    def __str__(self) -> str:
        return f"{self.order} — {self.get_carrier_display()}"
