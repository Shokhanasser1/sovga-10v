from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.catalog.models import Brand, Category, Variant


class ExchangeRate(models.Model):
    date = models.DateField(unique=True)
    cbu_rate = models.DecimalField(max_digits=12, decimal_places=2, help_text="Сумов за 1 USD по ЦБ")
    spread_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        get_latest_by = "date"

    def __str__(self) -> str:
        return f"{self.date}: {self.cbu_rate}"

    @property
    def effective_rate(self) -> Decimal:
        return (self.cbu_rate * (1 + self.spread_pct / 100)).quantize(Decimal("0.01"))


class MarkupRule(models.Model):
    variant = models.ForeignKey(
        Variant, null=True, blank=True, on_delete=models.CASCADE, related_name="markup_rules"
    )
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.CASCADE)
    markup_pct = models.DecimalField(max_digits=6, decimal_places=2)
    min_margin_uzs = models.PositiveBigIntegerField(default=0)
    rounding_step_uzs = models.PositiveIntegerField(default=1000)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant"], condition=Q(is_active=True), name="unique_active_variant_markup"
            ),
            models.UniqueConstraint(
                fields=["category"], condition=Q(is_active=True), name="unique_active_category_markup"
            ),
            models.UniqueConstraint(
                fields=["brand"], condition=Q(is_active=True), name="unique_active_brand_markup"
            ),
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(
                    is_active=True, variant__isnull=True, category__isnull=True, brand__isnull=True
                ),
                name="single_active_global_markup",
            ),
        ]

    def __str__(self) -> str:
        scope = self.variant or self.category or self.brand or "все товары"
        return f"{scope}: +{self.markup_pct}%"

    def clean(self) -> None:
        scopes = [value for value in (self.variant_id, self.category_id, self.brand_id) if value]
        if len(scopes) > 1:
            raise ValidationError("Укажите не больше одной области: вариант, категория или бренд")


class PriceSnapshot(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="price_snapshots")
    price_uzs = models.PositiveBigIntegerField()
    cost_usd = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=12, decimal_places=2, help_text="Курс с учётом спреда")
    offer = models.ForeignKey("sourcing.Offer", null=True, blank=True, on_delete=models.SET_NULL)
    markup_rule = models.ForeignKey(MarkupRule, null=True, blank=True, on_delete=models.SET_NULL)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-computed_at", "-pk"]

    def __str__(self) -> str:
        return f"{self.variant}: {self.price_uzs} сум"
