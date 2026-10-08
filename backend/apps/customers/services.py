from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Customer

# Отдельное пространство логинов: вход по коду никогда не попадёт в учётку сотрудника.
USERNAME_PREFIX = "customer_"


class AccountConflict(Exception):
    """Покупательский логин занят учёткой с правами или паролем — автоматически не входим."""


@transaction.atomic
def customer_for_phone(phone: str) -> Customer:
    """Покупатель по номеру; при первом входе создаётся вместе с пользователем без пароля."""
    existing = Customer.objects.select_related("user").filter(phone=phone).first()
    if existing:
        _ensure_plain_customer(existing.user)
        return existing
    user_model = get_user_model()
    username = f"{USERNAME_PREFIX}{phone}"
    user = user_model.objects.filter(username=username).first()
    if user is None:
        user = user_model(username=username)
        user.set_unusable_password()
        user.save()
    _ensure_plain_customer(user)
    return Customer.objects.create(user=user, phone=phone)


def _ensure_plain_customer(user) -> None:
    """Код на телефон слабее пароля: учётки с правами или паролем так не открываем."""
    if user.is_staff or user.is_superuser or user.has_usable_password():
        raise AccountConflict("Номер привязан к служебной учётной записи. Обратитесь к администратору.")
