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

    class Meta:
        verbose_name = "ссылка на Telegram"
        verbose_name_plural = "ссылки на Telegram"

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.customer or self.supplier}"


class DemoMessage(models.Model):
    """Учебный режим без токена: что бот отправил бы в чат и что ему ответили из «Имитации Telegram»."""

    class Direction(models.TextChoices):
        OUT = "out", "Бот → чат"
        IN = "in", "Чат → бот"

    chat_id = models.BigIntegerField(db_index=True)
    direction = models.CharField(max_length=3, choices=Direction.choices)
    text = models.TextField()
    reply_markup = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]
        verbose_name = "сообщение (имитация Telegram)"
        verbose_name_plural = "имитация Telegram"

    def __str__(self) -> str:
        return f"{self.chat_id}: {self.text[:40]}"

    def buttons(self) -> list[dict]:
        rows = (self.reply_markup or {}).get("inline_keyboard", [])
        return [button for row in rows for button in row if "callback_data" in button]
