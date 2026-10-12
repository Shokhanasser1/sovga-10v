from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Brand, Category


class GiftPolicy(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.CASCADE)
    min_price_uzs = models.PositiveBigIntegerField(null=True, blank=True)
    max_price_uzs = models.PositiveBigIntegerField(null=True, blank=True)
    budget_pct_of_net_margin = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    budget_cap_uzs = models.PositiveBigIntegerField()
    priority = models.IntegerField(default=0)
    active_from = models.DateTimeField(null=True, blank=True)
    active_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "правило подарка"
        verbose_name_plural = "правила подарков"

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        errors = {}
        if (
            self.min_price_uzs is not None
            and self.max_price_uzs is not None
            and self.min_price_uzs > self.max_price_uzs
        ):
            errors["max_price_uzs"] = "Максимальная цена меньше минимальной"
        if self.active_from and self.active_to and self.active_from >= self.active_to:
            errors["active_to"] = "Окончание раньше начала"
        if errors:
            raise ValidationError(errors)
