from django.conf import settings
from django.db import models


class Customer(models.Model):
    """Покупатель — пользователь Django без пароля, входит по коду на телефон."""

    class Language(models.TextChoices):
        RU = "ru", "Русский"
        UZ = "uz", "Oʻzbekcha"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer", verbose_name="пользователь"
    )
    phone = models.CharField(max_length=13, unique=True, verbose_name="телефон")
    name = models.CharField(max_length=100, blank=True, verbose_name="имя")
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.RU, verbose_name="язык")
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, verbose_name="чат Telegram")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="создан")

    class Meta:
        verbose_name = "покупатель"
        verbose_name_plural = "покупатели"

    def __str__(self) -> str:
        return self.name or self.phone


class Address(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="addresses", verbose_name="покупатель"
    )
    text = models.CharField(max_length=300, verbose_name="адрес")
    landmark = models.CharField(
        max_length=200, blank=True, help_text="Ориентир: «напротив школы №110»", verbose_name="ориентир"
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="широта")
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="долгота")
    last_used_at = models.DateTimeField(auto_now=True, verbose_name="последний раз")

    class Meta:
        verbose_name = "адрес"
        verbose_name_plural = "адреса"
        ordering = ["-last_used_at"]

    def __str__(self) -> str:
        return self.text


class OtpCode(models.Model):
    """Код входа. Хранится только HMAC-хэш кода."""

    phone = models.CharField(max_length=13, db_index=True, verbose_name="телефон")
    code_hash = models.CharField(max_length=64, verbose_name="хеш кода")
    channel = models.CharField(max_length=20, blank=True, verbose_name="канал")
    created_at = models.DateTimeField(verbose_name="создан")
    expires_at = models.DateTimeField(verbose_name="действует до")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="попыток")
    consumed_at = models.DateTimeField(null=True, blank=True, verbose_name="использован")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес")

    class Meta:
        verbose_name = "код входа"
        verbose_name_plural = "коды входа"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.phone} {self.created_at:%Y-%m-%d %H:%M}"


class OtpPhone(models.Model):
    """Строка-замок на номер: выдача кодов по одному номеру идёт строго по очереди."""

    phone = models.CharField(max_length=13, primary_key=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "номер для кодов входа"
        verbose_name_plural = "номера для кодов входа"

    def __str__(self) -> str:
        return self.phone
