from datetime import datetime, timedelta
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.catalog.models import Variant


class Supplier(models.Model):
    class Connector(models.TextChoices):
        API = "api", "API (JSON по ссылке)"
        SHEET = "sheet", "Google Sheets / CSV по ссылке"
        FILE = "file", "Excel/CSV-файл вручную"
        TELEGRAM = "telegram", "Telegram / вручную"

    DEFAULT_TTL_HOURS = {"api": 1, "sheet": 24, "file": 24, "telegram": 6}

    name = models.CharField(max_length=200)
    connector_type = models.CharField(max_length=10, choices=Connector.choices)
    feed_url = models.URLField(blank=True, help_text="CSV (Google Sheets) или JSON (API)")
    columns = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"code": "Артикул", "name": "Наименование", "price": "Цена $", "qty": "Остаток"}',
    )
    ttl_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="Пусто — значение по умолчанию для типа подключения"
    )
    reliability = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.10")), MaxValueValidator(Decimal("1.00"))],
        help_text="1.00 — не подводит; меньше — чаще отказывает",
    )
    lead_time_days = models.PositiveIntegerField(default=1)
    payment_terms = models.CharField(max_length=200, blank=True)
    contact = models.CharField(max_length=200, blank=True)
    telegram_chat_id = models.BigIntegerField(
        null=True, blank=True, help_text="Заполняет бот, когда поставщик открывает ссылку для подключения"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "поставщик"
        verbose_name_plural = "поставщики"

    def __str__(self) -> str:
        return self.name

    @property
    def effective_ttl(self) -> timedelta:
        hours = self.ttl_hours
        if hours is None:
            hours = self.DEFAULT_TTL_HOURS[self.connector_type]
        return timedelta(hours=hours)


class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "склад"
        verbose_name_plural = "склады"

    def __str__(self) -> str:
        return self.name


class Offer(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="offers")
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True, on_delete=models.CASCADE, related_name="offers"
    )
    warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True, on_delete=models.CASCADE, related_name="offers"
    )
    cost_usd = models.DecimalField(max_digits=12, decimal_places=2)
    qty_available = models.PositiveIntegerField(default=0)
    lead_time_days = models.PositiveIntegerField(default=0)
    last_confirmed_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "предложение"
        verbose_name_plural = "предложения"
        constraints = [
            models.CheckConstraint(
                condition=Q(supplier__isnull=False, warehouse__isnull=True)
                | Q(supplier__isnull=True, warehouse__isnull=False),
                name="offer_has_exactly_one_source",
                violation_error_message="Укажите либо поставщика, либо свой склад",
            ),
            models.UniqueConstraint(fields=["variant", "supplier"], name="unique_supplier_offer"),
            models.UniqueConstraint(fields=["variant", "warehouse"], name="unique_warehouse_offer"),
        ]

    def __str__(self) -> str:
        return f"{self.variant} ← {self.warehouse or self.supplier}"

    @property
    def is_own(self) -> bool:
        return self.warehouse_id is not None

    def is_fresh(self, now: datetime) -> bool:
        if self.is_own:
            return True
        return now - self.last_confirmed_at <= self.supplier.effective_ttl


class SupplierSkuMap(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="sku_maps")
    supplier_code = models.CharField(max_length=100)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="supplier_codes")

    class Meta:
        verbose_name = "артикул поставщика"
        verbose_name_plural = "артикулы поставщиков"
        constraints = [
            models.UniqueConstraint(fields=["supplier", "supplier_code"], name="unique_supplier_code")
        ]

    def __str__(self) -> str:
        return f"{self.supplier}: {self.supplier_code} → {self.variant}"


class SupplierFeedRun(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="feed_runs")
    started_at = models.DateTimeField()
    rows_total = models.PositiveIntegerField(default=0)
    rows_matched = models.PositiveIntegerField(default=0)
    rows_unmatched = models.PositiveIntegerField(default=0)
    rows_invalid = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        verbose_name = "загрузка прайса"
        verbose_name_plural = "загрузки прайсов"
        ordering = ["-started_at", "-pk"]

    def __str__(self) -> str:
        return f"{self.supplier} — {self.started_at:%Y-%m-%d %H:%M}"


class SupplierFeedRow(models.Model):
    class Status(models.TextChoices):
        MATCHED = "matched", "Сопоставлена"
        UNMATCHED = "unmatched", "Ждёт сопоставления"
        INVALID = "invalid", "Ошибка в строке"

    run = models.ForeignKey(SupplierFeedRun, on_delete=models.CASCADE, related_name="rows")
    supplier_code = models.CharField(max_length=100)
    name = models.CharField(max_length=300, blank=True)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    qty = models.PositiveIntegerField(null=True, blank=True)
    raw = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status.choices)
    error = models.CharField(max_length=200, blank=True)
    variant = models.ForeignKey(Variant, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "строка прайса"
        verbose_name_plural = "строки прайсов"

    def __str__(self) -> str:
        return f"{self.supplier_code} {self.name}".strip()


class Reservation(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="reservations")
    qty = models.PositiveIntegerField()
    ref = models.CharField(max_length=64, help_text="Корзина или заказ")
    is_soft = models.BooleanField(help_text="Товар поставщика до его подтверждения")
    expires_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "резерв"
        verbose_name_plural = "резервы"

    def __str__(self) -> str:
        return f"{self.ref}: {self.offer} × {self.qty}"
