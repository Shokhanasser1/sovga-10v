"""Сотрудники магазина: роли (группы с правами) и учебные учётные записи.

Роли нужны и настоящему магазину: администратор создаёт сотрудника в админке и ставит ему группу.
Готовые учётные записи — только в учебном режиме: пароли случайные и лежат в файле вне git
(`backend/demo-accounts.txt`). Пересоздание базы берёт пароли из файла — учителю не нужно учить новые.
"""

import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

# Роль → права: «приложение» — все права приложения, «приложение.право» — одно право.
ROLES: dict[str, list[str]] = {
    "Менеджер": [
        "catalog", "pricing", "sourcing", "promo", "inventory", "orders", "warranty", "delivery", "bot",
        "customers.view_customer", "customers.change_customer", "customers.view_address",
        "payments.view_payment", "notifications.view_outboxevent",
    ],
    "Оператор": [
        "orders.view_order", "orders.change_order", "orders.view_orderline", "orders.view_returnrequest",
        "warranty", "bot.view_demomessage", "bot.change_demomessage",
        "customers.view_customer", "customers.view_address", "inventory.view_inventoryunit",
        "catalog.view_productmodel", "catalog.view_variant", "sourcing.view_supplier", "sourcing.view_offer",
        "payments.view_payment",
    ],
    "Бухгалтер": [
        "orders.view_salesreport", "orders.view_order", "orders.view_orderline", "orders.view_returnrequest",
        "payments.view_payment", "customers.view_customer",
    ],
}


@dataclass(frozen=True)
class Account:
    title: str
    username: str
    role: str | None  # None — администратор: все права


DEMO_ACCOUNTS = [
    Account("Администратор", "admin", None),
    Account("Менеджер", "manager", "Менеджер"),
    Account("Оператор", "operator", "Оператор"),
    Account("Бухгалтер", "accountant", "Бухгалтер"),
]
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # без похожих 0/o, 1/l/i — легко продиктовать ученикам
LINE = re.compile(r"логин:\s*(\S+),\s*пароль:\s*(\S+)")


def _permissions(spec: list[str]) -> list[Permission]:
    condition = Q(pk__in=[])
    for item in spec:
        app, _, codename = item.partition(".")
        condition |= Q(content_type__app_label=app, codename=codename) if codename else Q(content_type__app_label=app)
    return list(Permission.objects.filter(condition))


def apply_roles() -> None:
    """Создаёт роли или возвращает им права из списка выше."""
    for name, spec in ROLES.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set(_permissions(spec))


def new_password() -> str:
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(3))


def read_passwords(path: Path) -> dict[str, str]:
    if not Path(path).exists():
        return {}
    return dict(LINE.findall(Path(path).read_text(encoding="utf-8")))


def _write(path: Path, passwords: dict[str, str]) -> None:
    lines = [
        "Учебные учётные записи магазина Sovgʻa. Файл не попадает в git — не публикуйте его.",
        "Админка: http://localhost:8000/admin",
        "",
        *(f"{account.title} — логин: {account.username}, пароль: {passwords[account.username]}"
          for account in DEMO_ACCOUNTS),
        "",
        "Покупатели — на витрине http://localhost:3000 по номеру 90 111 01 01 (до 90 111 01 12):",
        "код входа покажется на экране.",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_demo_staff(path: Path) -> dict[str, str]:
    """Учебные сотрудники. Новому — пароль из файла или случайный; у существующего пароль не трогаем."""
    apply_roles()
    saved = read_passwords(path)
    passwords = {}
    for account in DEMO_ACCOUNTS:
        user, created = get_user_model().objects.get_or_create(username=account.username)
        user.first_name, user.is_staff, user.is_superuser = account.title, True, account.role is None
        known = saved.get(account.username)
        if created or not known:
            known = known or new_password()
            user.set_password(known)
        user.save()
        user.groups.set([Group.objects.get(name=account.role)] if account.role else [])
        passwords[account.username] = known
    _write(path, passwords)
    return passwords
