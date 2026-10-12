from django.db import models


class Shipment(models.Model):
    """Передача заказа в доставку: свой курьер или служба доставки."""

    class Carrier(models.TextChoices):
        OWN = "own", "Свой курьер"
        SERVICE = "service", "Служба доставки"

    order = models.OneToOneField(
        "orders.Order", on_delete=models.PROTECT, related_name="shipment", verbose_name="заказ"
    )
    carrier = models.CharField(max_length=20, choices=Carrier.choices, verbose_name="способ доставки")
    courier_name = models.CharField(max_length=100, blank=True, verbose_name="курьер")
    courier_phone = models.CharField(max_length=13, blank=True, verbose_name="телефон курьера")
    service_name = models.CharField(max_length=100, blank=True, verbose_name="служба доставки")
    tracking = models.CharField(
        max_length=64, blank=True, help_text="Номер накладной службы доставки", verbose_name="накладная"
    )
    cost_uzs = models.PositiveBigIntegerField(
        default=0, help_text="Сколько доставка стоила магазину", verbose_name="стоимость доставки, сум"
    )
    handed_at = models.DateTimeField(verbose_name="передан")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="доставлен")

    class Meta:
        verbose_name = "доставка"
        verbose_name_plural = "доставки"

    def __str__(self) -> str:
        return f"{self.order} — {self.get_carrier_display()}"
