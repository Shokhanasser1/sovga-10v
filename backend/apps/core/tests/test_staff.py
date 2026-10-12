"""Сотрудники: роли с правами и учебные учётные записи с паролями в файле вне git."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.core.staff import ROLES, apply_roles, read_passwords

pytestmark = pytest.mark.django_db
User = get_user_model()

DESK = reverse("admin:orders_operatordesk_changelist")
REPORT = reverse("admin:orders_salesreport_changelist")
SIMULATOR = reverse("admin:bot_demomessage_changelist")
PRODUCTS = reverse("admin:catalog_productmodel_changelist")
ADD_PRODUCT = reverse("admin:catalog_productmodel_add")
WARRANTY = reverse("admin:warranty_warrantycase_changelist")
PAYMENTS = reverse("admin:payments_payment_changelist")
USERS = reverse("admin:auth_user_changelist")


@pytest.fixture
def accounts_file(settings, tmp_path):
    settings.DEMO_ACCOUNTS_FILE = tmp_path / "demo-accounts.txt"
    return settings.DEMO_ACCOUNTS_FILE


def employee(role: str) -> Client:
    apply_roles()
    user = User.objects.create_user("employee", password="x", is_staff=True)
    user.groups.add(Group.objects.get(name=role))
    client = Client()
    client.force_login(user)
    return client


def status(client: Client, url: str) -> int:
    return client.get(url).status_code


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        ("Менеджер", [DESK, REPORT, SIMULATOR, PRODUCTS, ADD_PRODUCT, WARRANTY, PAYMENTS], [USERS]),
        ("Оператор", [DESK, SIMULATOR, WARRANTY, PRODUCTS], [REPORT, ADD_PRODUCT, USERS]),
        ("Бухгалтер", [REPORT, PAYMENTS], [DESK, SIMULATOR, PRODUCTS, USERS]),
    ],
)
def test_each_role_opens_only_its_own_pages(settings, role, allowed, denied):
    settings.DEMO_MODE = True
    client = employee(role)

    assert {url: status(client, url) for url in allowed} == {url: 200 for url in allowed}
    assert {url: status(client, url) for url in denied} == {url: 403 for url in denied}


def test_roles_are_rebuilt_without_duplicates():
    apply_roles()
    apply_roles()

    assert set(Group.objects.values_list("name", flat=True)) == set(ROLES)


def test_learning_mode_creates_every_employee_with_a_password_from_the_file(settings, accounts_file):
    settings.DEMO_MODE = True

    call_command("seed_demo", stdout=None)

    passwords = read_passwords(accounts_file)
    assert set(passwords) == {"admin", "manager", "operator", "accountant"}
    assert all(len(password) >= 12 for password in passwords.values())
    assert User.objects.get(username="admin").is_superuser
    assert list(User.objects.get(username="operator").groups.values_list("name", flat=True)) == ["Оператор"]
    assert Client().login(username="accountant", password=passwords["accountant"])
    text = accounts_file.read_text(encoding="utf-8")
    assert "http://localhost:8000/admin" in text and "90 111 01 01" in text


def test_passwords_survive_a_fresh_database(settings, accounts_file):
    settings.DEMO_MODE = True
    call_command("seed_demo", stdout=None)
    before = read_passwords(accounts_file)

    User.objects.filter(is_staff=True).delete()  # как после reset-demo.cmd: базы нет, файл остался
    call_command("seed_demo", stdout=None)

    assert read_passwords(accounts_file) == before
    assert Client().login(username="manager", password=before["manager"])


def test_existing_employee_keeps_a_changed_password(settings, accounts_file):
    settings.DEMO_MODE = True
    call_command("seed_demo", stdout=None)
    manager = User.objects.get(username="manager")
    manager.set_password("teacher-chose-this")
    manager.save()

    call_command("seed_demo", stdout=None)

    assert Client().login(username="manager", password="teacher-chose-this")


def test_real_shop_gets_roles_but_no_ready_made_accounts(settings, accounts_file):
    settings.DEMO_MODE = False

    call_command("seed_demo", stdout=None)

    assert set(Group.objects.values_list("name", flat=True)) == set(ROLES)
    assert not User.objects.filter(is_staff=True).exists()
    assert not accounts_file.exists()


def test_migrate_creates_roles_for_a_real_shop_too():
    """Роли приходят с migrate — настоящему магазину не нужен seed_demo с учебным каталогом."""
    Group.objects.all().delete()

    call_command("migrate", verbosity=0)

    assert set(Group.objects.values_list("name", flat=True)) == set(ROLES)
    assert Group.objects.get(name="Бухгалтер").permissions.filter(codename="view_salesreport").exists()
