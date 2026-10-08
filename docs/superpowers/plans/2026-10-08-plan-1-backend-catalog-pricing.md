# План 1. Бэкенд: каркас, каталог, цены, подарки — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Работающий Django-бэкенд с моделью каталога (типизированные атрибуты, вариации, совместимость, сравнение), расчётом цены в сумах, бюджетом подарка, админкой и публичным API каталога.

**Architecture:** Модульный монолит (спецификация, раздел 4). Каждое Django-приложение отдаёт наружу только публичные функции своих модулей (`attributes`, `rules`, `compatibility`, `comparison`, `calculator`, `markup`, `cbu`, `budget`, `selection`); чистая логика отделена от ORM и тестируется без БД.

**Tech Stack:** Python 3.14, Django 6.0, Django REST Framework 3.16, django-environ, pytest + pytest-django, Hypothesis, requests.

**Спецификация:** `docs/superpowers/specs/2026-10-08-electronics-store-uz-design.md`

## Global Constraints

- Python 3.14, Django `>=6.0,<6.1`, DRF `>=3.16,<3.17`.
- Суммы в сумах — целые числа (`PositiveBigIntegerField` / `int`); USD — `Decimal`, 2 знака. `float` для денег запрещён.
- Витрина и чек — только UZS; USD только во внутренних расчётах и админке.
- Переводимые поля — пары `*_ru` / `*_uz`.
- У каждого SKU обязательны `mxik_code` (ИКПУ, ровно 17 цифр) и `package_code` (только цифры).
- Приложения обращаются друг к другу только через публичные функции модулей, перечисленные выше.
- API по умолчанию закрыт (`IsAuthenticated`); публичные эндпоинты явно помечены `AllowAny` и только читают.
- Секреты — только из окружения; `.env` не коммитится.
- Сообщения об ошибках — на русском.
- Коммиты: `<type>: <description>`, типы feat, fix, refactor, docs, test, chore, perf, ci.
- Тесты локально идут на SQLite; Postgres-специфичное (GIN-индексы) — в Плане 2.

Команды даны для Git Bash из каталога `backend/`. В PowerShell 5.1 вместо `&&` используйте `;`.

## Структура файлов

```
.gitignore
backend/
  manage.py
  requirements.txt            рантайм-зависимости
  requirements-dev.txt        + тестовые
  pyproject.toml              настройки pytest
  .env.example
  conftest.py                 общие фикстуры каталога
  config/
    __init__.py  settings.py  settings_test.py  urls.py  wsgi.py  asgi.py
  apps/
    __init__.py
    core/        apps.py views.py urls.py tests/test_health.py tests/test_admin.py
    catalog/
      apps.py
      attributes.py           валидация значений атрибутов, canonical_key
      rules.py                язык правил совместимости
      models.py               Category, AttributeDefinition, Brand, ProductModel, Variant,
                              AccessoryCompat, CompatRule
      compatibility.py        is_compatible, compatible_accessories
      comparison.py           build_comparison, compare_variants
      admin.py serializers.py views.py urls.py
      tests/ test_categories.py test_attributes.py test_products.py test_rules.py
             test_compatibility.py test_comparison.py test_api.py
    pricing/
      apps.py
      calculator.py           sale_price_uzs, needs_reprice
      models.py               ExchangeRate, MarkupRule
      markup.py               resolve_markup_rule, price_for
      cbu.py                  parse_usd_rate, fetch_usd_rate
      management/commands/fetch_cbu_rate.py
      admin.py
      tests/ test_calculator.py test_markup.py test_cbu.py
    promo/
      apps.py
      budget.py               gift_budget_uzs
      models.py               GiftPolicy
      selection.py            select_gift_policy
      admin.py
      tests/ test_budget.py test_selection.py
```

---

### Task 1: Каркас проекта и health-эндпоинт

**Files:**
- Create: `.gitignore`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/pyproject.toml`, `backend/.env.example`, `backend/manage.py`, `backend/config/__init__.py`, `backend/config/settings.py`, `backend/config/settings_test.py`, `backend/config/urls.py`, `backend/config/wsgi.py`, `backend/config/asgi.py`, `backend/apps/__init__.py`, `backend/apps/core/__init__.py`, `backend/apps/core/apps.py`, `backend/apps/core/views.py`, `backend/apps/core/urls.py`, `backend/apps/core/tests/__init__.py`
- Test: `backend/apps/core/tests/test_health.py`

**Interfaces:**
- Produces: `GET /api/health/` → `{"status": "ok"}`; настройки `config.settings` (читает окружение) и `config.settings_test` (для pytest); `REST_FRAMEWORK` с закрытым по умолчанию доступом.

- [ ] **Step 1: Окружение и зависимости**

`.gitignore` (корень репозитория):
```gitignore
.venv/
__pycache__/
*.pyc
.env
db.sqlite3
.pytest_cache/
.hypothesis/
staticfiles/
node_modules/
```

`backend/requirements.txt`:
```
Django>=6.0,<6.1
djangorestframework>=3.16,<3.17
django-environ>=0.13,<0.14
psycopg2-binary>=2.9.11,<2.10
requests>=2.32,<3
```

`backend/requirements-dev.txt`:
```
-r requirements.txt
pytest>=9,<10
pytest-django>=4.12,<5
hypothesis>=6.100,<7
```

`backend/pyproject.toml`:
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings_test"
python_files = ["test_*.py"]
addopts = "-q"
```

`backend/.env.example`:
```
DEBUG=true
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
# DATABASE_URL=postgres://shop:shop@localhost:5432/shop
# TELEGRAM_BOT_TOKEN=   # только новый токен после /revoke, файл .env не коммитится
```

Run: `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt`
Expected: зависимости установлены без ошибок.

- [ ] **Step 2: Написать падающий тест**

`backend/apps/core/tests/test_health.py`:
```python
def test_health_returns_ok(client):
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```
(`backend/apps/__init__.py`, `backend/apps/core/__init__.py`, `backend/apps/core/tests/__init__.py` — пустые.)

- [ ] **Step 3: Запустить — тест должен упасть**

Run: `.venv/Scripts/python -m pytest apps/core/tests/test_health.py`
Expected: FAIL / ошибка конфигурации — нет модуля `config.settings_test`.

- [ ] **Step 4: Реализация**

`backend/manage.py`:
```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`backend/config/__init__.py` — пустой.

`backend/config/settings.py`:
```python
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if env("DATABASE_URL", default=None):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский"), ("uz", "Oʻzbekcha")]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
}
```

`backend/config/settings_test.py`:
```python
import os

os.environ.setdefault("SECRET_KEY", "test-only-not-a-secret")

from config.settings import *  # noqa: E402,F403
```

`backend/config/urls.py`:
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
]
```

`backend/config/wsgi.py`:
```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
```

`backend/config/asgi.py`:
```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
```

`backend/apps/core/apps.py`:
```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
```

`backend/apps/core/views.py`:
```python
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
```

`backend/apps/core/urls.py`:
```python
from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
]
```

- [ ] **Step 5: Запустить — тест проходит**

Run: `.venv/Scripts/python -m pytest apps/core/tests/test_health.py`
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add .gitignore backend
git commit -m "chore: scaffold django backend with health endpoint"
```

---

### Task 2: Категории и определения атрибутов

**Files:**
- Create: `backend/apps/catalog/__init__.py`, `backend/apps/catalog/apps.py`, `backend/apps/catalog/models.py`, `backend/apps/catalog/tests/__init__.py`
- Modify: `backend/config/settings.py` (INSTALLED_APPS)
- Test: `backend/apps/catalog/tests/test_categories.py`

**Interfaces:**
- Produces: `Category.lineage() -> list[Category]` (от корня к себе), `Category.effective_attributes() -> list[AttributeDefinition]` (с наследованием, сортировка `(sort_order, code)`), `AttributeDefinition.Type / Level / Comparison` (TextChoices).

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/catalog/tests/test_categories.py`:
```python
import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import AttributeDefinition, Category

pytestmark = pytest.mark.django_db


def make_category(slug, parent=None):
    return Category.objects.create(slug=slug, name_ru=slug, name_uz=slug, parent=parent)


def make_attr(category, code, **kwargs):
    kwargs.setdefault("type", AttributeDefinition.Type.NUMBER)
    return AttributeDefinition.objects.create(
        category=category, code=code, name_ru=code, name_uz=code, **kwargs
    )


def test_effective_attributes_inherit_from_parent():
    electronics = make_category("electronics")
    phones = make_category("phones", parent=electronics)
    make_attr(electronics, "weight_g", sort_order=20)
    make_attr(phones, "battery_mah", sort_order=10)

    codes = [d.code for d in phones.effective_attributes()]

    assert codes == ["battery_mah", "weight_g"]


def test_child_definition_overrides_parent_with_same_code():
    root = make_category("root")
    child = make_category("child", parent=root)
    make_attr(root, "screen", unit="in")
    make_attr(child, "screen", unit="mm")

    [definition] = child.effective_attributes()

    assert definition.unit == "mm"


def test_lineage_goes_from_root_to_self():
    root = make_category("root")
    child = make_category("child", parent=root)
    grandchild = make_category("grandchild", parent=child)

    assert [c.slug for c in grandchild.lineage()] == ["root", "child", "grandchild"]


def test_category_cannot_become_its_own_descendant():
    root = make_category("root")
    child = make_category("child", parent=root)
    root.parent = child

    with pytest.raises(ValidationError) as exc:
        root.full_clean()

    assert "parent" in exc.value.message_dict


def test_variant_axis_must_be_variant_level():
    category = make_category("phones")
    definition = AttributeDefinition(
        category=category, code="storage_gb", name_ru="Память", name_uz="Xotira",
        type=AttributeDefinition.Type.NUMBER, is_variant_axis=True,
        level=AttributeDefinition.Level.MODEL,
    )

    with pytest.raises(ValidationError) as exc:
        definition.full_clean()

    assert "level" in exc.value.message_dict


def test_enum_requires_values():
    category = make_category("phones")
    definition = AttributeDefinition(
        category=category, code="color", name_ru="Цвет", name_uz="Rang",
        type=AttributeDefinition.Type.ENUM, enum_values=[],
    )

    with pytest.raises(ValidationError) as exc:
        definition.full_clean()

    assert "enum_values" in exc.value.message_dict


def test_comparison_direction_only_for_numbers():
    category = make_category("phones")
    definition = AttributeDefinition(
        category=category, code="chipset", name_ru="Чипсет", name_uz="Chipset",
        type=AttributeDefinition.Type.TEXT,
        comparison=AttributeDefinition.Comparison.HIGHER_BETTER,
    )

    with pytest.raises(ValidationError) as exc:
        definition.full_clean()

    assert "comparison" in exc.value.message_dict
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_categories.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.catalog'`.

- [ ] **Step 3: Реализация**

`backend/apps/catalog/apps.py`:
```python
from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "apps.catalog"
```

В `backend/config/settings.py` добавить `"apps.catalog",` в `INSTALLED_APPS` после `"apps.core",`.

`backend/apps/catalog/models.py`:
```python
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    slug = models.SlugField(unique=True)
    name_ru = models.CharField(max_length=200)
    name_uz = models.CharField(max_length=200)
    is_serialized = models.BooleanField(
        default=False, help_text="Поштучный учёт по IMEI/SN (телефоны, планшеты)"
    )

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name_ru

    def lineage(self) -> list["Category"]:
        """Цепочка категорий от корня до этой; устойчива к циклам."""
        chain: list[Category] = []
        seen: set[int | None] = set()
        node: Category | None = self
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            chain.append(node)
            node = node.parent
        return chain[::-1]

    def effective_attributes(self) -> list["AttributeDefinition"]:
        """Атрибуты с наследованием; дочерняя категория переопределяет родителя по code."""
        by_code: dict[str, AttributeDefinition] = {}
        for category in self.lineage():
            for definition in category.attribute_definitions.all():
                by_code[definition.code] = definition
        return sorted(by_code.values(), key=lambda d: (d.sort_order, d.code))

    def clean(self) -> None:
        if self.parent is None or self.pk is None:
            return
        if any(category.pk == self.pk for category in self.parent.lineage()):
            raise ValidationError(
                {"parent": "Категория не может быть вложена в саму себя или своего потомка"}
            )


class AttributeDefinition(models.Model):
    class Type(models.TextChoices):
        NUMBER = "number", "Число"
        ENUM = "enum", "Список"
        BOOL = "bool", "Да/нет"
        TEXT = "text", "Текст"

    class Level(models.TextChoices):
        MODEL = "model", "Модель"
        VARIANT = "variant", "Вариант (SKU)"

    class Comparison(models.TextChoices):
        HIGHER_BETTER = "higher_better", "Больше — лучше"
        LOWER_BETTER = "lower_better", "Меньше — лучше"
        NONE = "none", "Не сравнивается"

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="attribute_definitions"
    )
    code = models.SlugField(max_length=64)
    name_ru = models.CharField(max_length=100)
    name_uz = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=Type.choices)
    unit = models.CharField(max_length=20, blank=True)
    enum_values = models.JSONField(default=list, blank=True)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.MODEL)
    is_variant_axis = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_facet = models.BooleanField(default=False)
    comparison = models.CharField(
        max_length=15, choices=Comparison.choices, default=Comparison.NONE
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "code"], name="unique_attribute_code_per_category"
            )
        ]

    def __str__(self) -> str:
        return f"{self.category} / {self.code}"

    def clean(self) -> None:
        errors = {}
        if self.is_variant_axis and self.level != self.Level.VARIANT:
            errors["level"] = "Ось вариации должна быть на уровне варианта"
        if self.type == self.Type.ENUM and not self.enum_values:
            errors["enum_values"] = "Для списка нужны допустимые значения"
        if self.comparison != self.Comparison.NONE and self.type != self.Type.NUMBER:
            errors["comparison"] = "Направление сравнения задаётся только для чисел"
        if errors:
            raise ValidationError(errors)
```

Run: `.venv/Scripts/python manage.py makemigrations catalog` (с `SECRET_KEY=dev` в окружении или `.env`)
Expected: `Migrations for 'catalog': 0001_initial.py`.

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_categories.py`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add categories and typed attribute definitions"
```

---

### Task 3: Валидатор значений атрибутов

**Files:**
- Create: `backend/apps/catalog/attributes.py`
- Modify: `backend/apps/catalog/models.py` (импорт, метод `AttributeDefinition.as_spec`)
- Test: `backend/apps/catalog/tests/test_attributes.py`

**Interfaces:**
- Produces: `AttrSpec(code: str, type: str, enum_values: tuple[str, ...] = (), is_required: bool = False)`; `validate_values(specs: Iterable[AttrSpec], values: object) -> list[str]` (пустой список = корректно; сначала неизвестные коды по алфавиту, затем ошибки по коду по алфавиту); `canonical_key(values: Mapping) -> str`; `AttributeDefinition.as_spec() -> AttrSpec` (оси вариации всегда обязательны).

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/catalog/tests/test_attributes.py`:
```python
from apps.catalog.attributes import AttrSpec, canonical_key, validate_values

SPECS = [
    AttrSpec("battery_mah", "number", is_required=True),
    AttrSpec("color", "enum", enum_values=("black", "white")),
    AttrSpec("nfc", "bool"),
    AttrSpec("chipset", "text"),
]


def test_valid_values_have_no_errors():
    values = {"battery_mah": 5000, "color": "black", "nfc": True, "chipset": "A18"}

    assert validate_values(SPECS, values) == []


def test_unknown_attribute_is_reported():
    assert validate_values(SPECS, {"battery_mah": 1, "ram": 8}) == ["ram: неизвестный атрибут"]


def test_missing_required_attribute_is_reported():
    assert validate_values(SPECS, {}) == ["battery_mah: обязательный атрибут"]


def test_none_counts_as_missing():
    assert validate_values(SPECS, {"battery_mah": None}) == ["battery_mah: обязательный атрибут"]


def test_bool_is_not_accepted_as_number():
    assert validate_values(SPECS, {"battery_mah": True}) == ["battery_mah: ожидается число"]


def test_enum_value_outside_list_is_reported():
    errors = validate_values(SPECS, {"battery_mah": 1, "color": "red"})

    assert errors == ["color: допустимо: black, white"]


def test_wrong_types_for_bool_and_text():
    errors = validate_values(SPECS, {"battery_mah": 1, "nfc": "yes", "chipset": 18})

    assert errors == ["chipset: ожидается строка", "nfc: ожидается true/false"]


def test_non_object_is_rejected():
    assert validate_values(SPECS, ["battery_mah"]) == ["ожидается объект {код: значение}"]


def test_canonical_key_ignores_key_order():
    assert canonical_key({"storage_gb": 256, "color": "black"}) == canonical_key(
        {"color": "black", "storage_gb": 256}
    )
    assert canonical_key({"b": 1, "a": "x"}) == '{"a": "x", "b": 1}'
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_attributes.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.catalog.attributes'`.

- [ ] **Step 3: Реализация**

`backend/apps/catalog/attributes.py`:
```python
"""Проверка значений атрибутов по их определениям. Чистые функции, без БД."""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class AttrSpec:
    code: str
    type: str  # number | enum | bool | text
    enum_values: tuple[str, ...] = ()
    is_required: bool = False


def _type_error(spec: AttrSpec, value: object) -> str | None:
    if spec.type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "ожидается число"
    elif spec.type == "bool":
        if not isinstance(value, bool):
            return "ожидается true/false"
    elif spec.type == "text":
        if not isinstance(value, str):
            return "ожидается строка"
    elif spec.type == "enum":
        if value not in spec.enum_values:
            return f"допустимо: {', '.join(spec.enum_values)}"
    return None


def validate_values(specs: Iterable[AttrSpec], values: object) -> list[str]:
    """Вернуть список ошибок; пустой список — значения корректны."""
    if not isinstance(values, Mapping):
        return ["ожидается объект {код: значение}"]
    by_code = {spec.code: spec for spec in specs}
    errors = [f"{code}: неизвестный атрибут" for code in sorted(values.keys() - by_code.keys())]
    for code, spec in sorted(by_code.items()):
        value = values.get(code)
        if value is None:
            if spec.is_required:
                errors.append(f"{code}: обязательный атрибут")
            continue
        problem = _type_error(spec, value)
        if problem:
            errors.append(f"{code}: {problem}")
    return errors


def canonical_key(values: Mapping) -> str:
    """Стабильная строка для сравнения наборов значений независимо от порядка ключей."""
    return json.dumps(values, sort_keys=True, ensure_ascii=False)
```

В `backend/apps/catalog/models.py` добавить импорт после `from django.db import models`:
```python

from .attributes import AttrSpec
```
и метод в `AttributeDefinition` (после `__str__`):
```python
    def as_spec(self) -> AttrSpec:
        return AttrSpec(
            code=self.code,
            type=self.type,
            enum_values=tuple(self.enum_values or ()),
            is_required=self.is_required or self.is_variant_axis,
        )
```

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/catalog`
Expected: `16 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add attribute value validator"
```

---

### Task 4: Бренды, модели товаров и варианты (SKU)

**Files:**
- Modify: `backend/apps/catalog/models.py` (импорты, `Status`, `Brand`, `ProductModel`, `Variant`)
- Create: `backend/conftest.py` (общие фикстуры)
- Test: `backend/apps/catalog/tests/test_products.py`

**Interfaces:**
- Consumes: `validate_values`, `canonical_key`, `AttributeDefinition.as_spec`, `Category.effective_attributes`.
- Produces: `Status` (DRAFT/ACTIVE/ARCHIVED), `Brand`, `ProductModel` (поля из спецификации 2.1; `clean()` проверяет атрибуты уровня model), `Variant` (`clean()` проверяет оси и атрибуты уровня variant, уникальность осей; `axes_key` заполняется в `clean()` и `save()`); фикстуры `phones`, `apple`, `iphone`, `make_variant(product, sku, axes, **kwargs)`; константа `MXIK = "08517001001000000"` в `backend/conftest.py`.

- [ ] **Step 1: Общие фикстуры**

`backend/conftest.py`:
```python
import pytest

from apps.catalog.models import AttributeDefinition, Brand, Category, ProductModel, Status, Variant

MXIK = "08517001001000000"


@pytest.fixture
def phones(db):
    category = Category.objects.create(
        slug="phones", name_ru="Смартфоны", name_uz="Smartfonlar", is_serialized=True
    )
    T, L, C = AttributeDefinition.Type, AttributeDefinition.Level, AttributeDefinition.Comparison
    definitions = [
        ("battery_mah", dict(type=T.NUMBER, is_required=True, comparison=C.HIGHER_BETTER, sort_order=10)),
        ("storage_gb", dict(type=T.NUMBER, level=L.VARIANT, is_variant_axis=True,
                            comparison=C.HIGHER_BETTER, sort_order=20)),
        ("color", dict(type=T.ENUM, enum_values=["black", "white"], level=L.VARIANT,
                       is_variant_axis=True, sort_order=30)),
        ("weight_g", dict(type=T.NUMBER, level=L.VARIANT, comparison=C.LOWER_BETTER, sort_order=40)),
    ]
    for code, kwargs in definitions:
        AttributeDefinition.objects.create(
            category=category, code=code, name_ru=code, name_uz=code, **kwargs
        )
    return category


@pytest.fixture
def apple(db):
    return Brand.objects.create(slug="apple", name="Apple")


@pytest.fixture
def iphone(phones, apple):
    return ProductModel.objects.create(
        category=phones, brand=apple, slug="iphone-16-pro",
        name_ru="iPhone 16 Pro", name_uz="iPhone 16 Pro",
        attributes={"battery_mah": 3582}, status=Status.ACTIVE,
    )


@pytest.fixture
def make_variant():
    def factory(product, sku, axes, **kwargs):
        kwargs.setdefault("mxik_code", MXIK)
        kwargs.setdefault("package_code", "1500")
        return Variant(product_model=product, sku=sku, axes=axes, **kwargs)

    return factory
```

- [ ] **Step 2: Написать падающие тесты**

`backend/apps/catalog/tests/test_products.py`:
```python
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

pytestmark = pytest.mark.django_db

BLACK_256 = {"storage_gb": 256, "color": "black"}


def test_product_model_validates_model_level_attributes(iphone):
    iphone.attributes = {"battery_mah": "big"}

    with pytest.raises(ValidationError) as exc:
        iphone.full_clean()

    assert exc.value.message_dict["attributes"] == ["battery_mah: ожидается число"]


def test_variant_level_attribute_is_unknown_on_model(iphone):
    iphone.attributes = {"battery_mah": 3582, "weight_g": 199}

    with pytest.raises(ValidationError) as exc:
        iphone.full_clean()

    assert exc.value.message_dict["attributes"] == ["weight_g: неизвестный атрибут"]


def test_variant_requires_all_axes(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", {"storage_gb": 256})

    with pytest.raises(ValidationError) as exc:
        variant.full_clean()

    assert exc.value.message_dict["axes"] == ["color: обязательный атрибут"]


def test_variant_attributes_are_validated_separately_from_axes(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", BLACK_256, attributes={"weight_g": "heavy"})

    with pytest.raises(ValidationError) as exc:
        variant.full_clean()

    assert exc.value.message_dict["attributes"] == ["weight_g: ожидается число"]


def test_duplicate_axes_rejected_regardless_of_key_order(iphone, make_variant):
    make_variant(iphone, "A", BLACK_256).save()
    duplicate = make_variant(iphone, "B", {"color": "black", "storage_gb": 256})

    with pytest.raises(ValidationError) as exc:
        duplicate.full_clean()

    assert "Вариант с такими осями уже существует" in exc.value.message_dict["axes"]


def test_duplicate_axes_blocked_at_database_level(iphone, make_variant):
    make_variant(iphone, "A", BLACK_256).save()

    with pytest.raises(IntegrityError):
        make_variant(iphone, "B", {"color": "black", "storage_gb": 256}).save()


def test_mxik_code_must_be_17_digits(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", BLACK_256, mxik_code="12345")

    with pytest.raises(ValidationError) as exc:
        variant.full_clean()

    assert "mxik_code" in exc.value.message_dict


def test_package_code_must_be_digits(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", BLACK_256, package_code="box")

    with pytest.raises(ValidationError) as exc:
        variant.full_clean()

    assert "package_code" in exc.value.message_dict


def test_valid_variant_passes_and_stores_canonical_axes_key(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", BLACK_256, attributes={"weight_g": 199})

    variant.full_clean()
    variant.save()

    assert variant.axes_key == '{"color": "black", "storage_gb": 256}'
```

- [ ] **Step 3: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_products.py`
Expected: FAIL — `ImportError: cannot import name 'Brand' from 'apps.catalog.models'`.

- [ ] **Step 4: Реализация**

В `backend/apps/catalog/models.py` заменить блок импортов на:
```python
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from .attributes import AttrSpec, canonical_key, validate_values
```
и добавить в конец файла:
```python


class Status(models.TextChoices):
    DRAFT = "draft", "Черновик"
    ACTIVE = "active", "Активен"
    ARCHIVED = "archived", "В архиве"


class Brand(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class ProductModel(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="product_models")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="product_models")
    slug = models.SlugField(max_length=200, unique=True)
    name_ru = models.CharField(max_length=200)
    name_uz = models.CharField(max_length=200)
    description_ru = models.TextField(blank=True)
    description_uz = models.TextField(blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    seo_title_ru = models.CharField(max_length=200, blank=True)
    seo_title_uz = models.CharField(max_length=200, blank=True)
    seo_description_ru = models.CharField(max_length=300, blank=True)
    seo_description_uz = models.CharField(max_length=300, blank=True)
    is_accessory = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    def __str__(self) -> str:
        return self.name_ru

    def clean(self) -> None:
        if self.category_id is None:
            return
        specs = [
            d.as_spec()
            for d in self.category.effective_attributes()
            if d.level == AttributeDefinition.Level.MODEL
        ]
        errors = validate_values(specs, self.attributes)
        if errors:
            raise ValidationError({"attributes": errors})


MXIK_VALIDATOR = RegexValidator(r"^\d{17}$", "ИКПУ (MXIK) — ровно 17 цифр")
DIGITS_VALIDATOR = RegexValidator(r"^\d+$", "Только цифры")


class Variant(models.Model):
    product_model = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=64, unique=True)
    barcodes = models.JSONField(default=list, blank=True)
    axes = models.JSONField(default=dict, blank=True)
    axes_key = models.CharField(max_length=500, editable=False)
    attributes = models.JSONField(default=dict, blank=True)
    mxik_code = models.CharField(max_length=17, validators=[MXIK_VALIDATOR])
    package_code = models.CharField(max_length=20, validators=[DIGITS_VALIDATOR])
    weight_g = models.PositiveIntegerField(null=True, blank=True)
    images = models.JSONField(default=list, blank=True)
    giftable = models.BooleanField(default=False, help_text="Может выдаваться подарком")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_model", "axes_key"], name="unique_variant_axes"
            )
        ]

    def __str__(self) -> str:
        return self.sku

    def save(self, *args, **kwargs) -> None:
        self.axes_key = canonical_key(self.axes)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        if self.product_model_id is None:
            return
        definitions = [
            d
            for d in self.product_model.category.effective_attributes()
            if d.level == AttributeDefinition.Level.VARIANT
        ]
        errors: dict[str, list[str]] = {}
        axis_errors = validate_values(
            [d.as_spec() for d in definitions if d.is_variant_axis], self.axes
        )
        if axis_errors:
            errors["axes"] = axis_errors
        attribute_errors = validate_values(
            [d.as_spec() for d in definitions if not d.is_variant_axis], self.attributes
        )
        if attribute_errors:
            errors["attributes"] = attribute_errors
        if "axes" not in errors:
            self.axes_key = canonical_key(self.axes)
            duplicate = (
                Variant.objects.filter(product_model_id=self.product_model_id, axes_key=self.axes_key)
                .exclude(pk=self.pk)
                .exists()
            )
            if duplicate:
                errors["axes"] = ["Вариант с такими осями уже существует"]
        if errors:
            raise ValidationError(errors)
```

Run: `.venv/Scripts/python manage.py makemigrations catalog`
Expected: `0002_...py` с `Brand`, `ProductModel`, `Variant`.

- [ ] **Step 5: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/catalog`
Expected: `25 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: add product models and variants with axis validation"
```

---

### Task 5: Совместимость аксессуаров

**Files:**
- Create: `backend/apps/catalog/rules.py`, `backend/apps/catalog/compatibility.py`
- Modify: `backend/apps/catalog/models.py` (импорт `validate_rule`, модели `AccessoryCompat`, `CompatRule`)
- Test: `backend/apps/catalog/tests/test_rules.py`, `backend/apps/catalog/tests/test_compatibility.py`

**Interfaces:**
- Produces: `OPERATORS` (`eq`, `lte`, `gte`, `in`); `validate_rule(conditions: object) -> list[str]`; `rule_matches(conditions: list[Mapping], device_attrs: Mapping, accessory_attrs: Mapping) -> bool` (условие: `{"attr", "op", "value" | "accessory_attr"}`, смысл — `device[attr] OP target`); модели `AccessoryCompat(accessory, device)`, `CompatRule(accessory, conditions, note)`; `is_compatible(accessory: ProductModel, device: ProductModel) -> bool`; `compatible_accessories(device: ProductModel) -> QuerySet[ProductModel]` (только активные аксессуары).

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/catalog/tests/test_rules.py`:
```python
from apps.catalog.rules import rule_matches, validate_rule

CHARGER_RULE = [
    {"attr": "charge_port", "op": "eq", "value": "usb-c"},
    {"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"},
]


def test_charger_matches_when_port_and_power_fit():
    assert rule_matches(CHARGER_RULE, {"charge_port": "usb-c", "max_charge_w": 27}, {"output_w": 30})


def test_charger_rejected_when_too_weak_for_device():
    assert not rule_matches(CHARGER_RULE, {"charge_port": "usb-c", "max_charge_w": 45}, {"output_w": 30})


def test_missing_device_attribute_never_matches():
    assert not rule_matches(CHARGER_RULE, {"charge_port": "usb-c"}, {"output_w": 30})


def test_in_operator():
    rule = [{"attr": "charge_port", "op": "in", "value": ["usb-c", "lightning"]}]

    assert rule_matches(rule, {"charge_port": "lightning"}, {})


def test_incomparable_types_do_not_raise():
    rule = [{"attr": "max_charge_w", "op": "lte", "value": 30}]

    assert not rule_matches(rule, {"max_charge_w": "fast"}, {})


def test_validate_rule_reports_structural_errors():
    errors = validate_rule([{"attr": "x", "op": "like", "value": 1, "accessory_attr": "y"}])

    assert errors == [
        "условие 1: op — одно из eq, lte, gte, in",
        "условие 1: нужно ровно одно из value / accessory_attr",
    ]


def test_empty_rule_is_invalid():
    assert validate_rule([]) == ["правило — непустой список условий"]


def test_valid_rule_has_no_errors():
    assert validate_rule(CHARGER_RULE) == []
```

`backend/apps/catalog/tests/test_compatibility.py`:
```python
import pytest
from django.core.exceptions import ValidationError

from apps.catalog.compatibility import compatible_accessories, is_compatible
from apps.catalog.models import AccessoryCompat, Brand, Category, CompatRule, ProductModel, Status

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    category = Category.objects.create(slug="all", name_ru="Все", name_uz="Hammasi")
    brand = Brand.objects.create(slug="any", name="Any")

    def factory(slug, is_accessory=False, **attributes):
        return ProductModel.objects.create(
            category=category, brand=brand, slug=slug, name_ru=slug, name_uz=slug,
            is_accessory=is_accessory, status=Status.ACTIVE, attributes=attributes,
        )

    return factory


def test_explicit_link_makes_case_compatible(product):
    phone = product("iphone-16")
    case = product("case-iphone-16", is_accessory=True)
    AccessoryCompat.objects.create(accessory=case, device=phone)

    assert is_compatible(case, phone)
    assert list(compatible_accessories(phone)) == [case]


def test_rule_links_new_phone_without_manual_work(product):
    charger = product("charger-30w", is_accessory=True, output_w=30)
    CompatRule.objects.create(accessory=charger, conditions=[
        {"attr": "charge_port", "op": "eq", "value": "usb-c"},
        {"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"},
    ])
    new_phone = product("galaxy-s26", charge_port="usb-c", max_charge_w=25)
    old_phone = product("iphone-11", charge_port="lightning", max_charge_w=18)

    assert list(compatible_accessories(new_phone)) == [charger]
    assert list(compatible_accessories(old_phone)) == []
    assert is_compatible(charger, new_phone)
    assert not is_compatible(charger, old_phone)


def test_inactive_accessories_are_hidden(product):
    phone = product("iphone-16")
    case = product("case-old", is_accessory=True)
    case.status = Status.ARCHIVED
    case.save()
    AccessoryCompat.objects.create(accessory=case, device=phone)

    assert list(compatible_accessories(phone)) == []


def test_explicit_link_rejects_non_accessory(product):
    link = AccessoryCompat(accessory=product("iphone-15"), device=product("iphone-16"))

    with pytest.raises(ValidationError) as exc:
        link.full_clean()

    assert "accessory" in exc.value.message_dict


def test_compat_rule_validates_conditions(product):
    rule = CompatRule(accessory=product("cable", is_accessory=True), conditions=[{"attr": "x"}])

    with pytest.raises(ValidationError) as exc:
        rule.full_clean()

    assert "conditions" in exc.value.message_dict
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_rules.py apps/catalog/tests/test_compatibility.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.catalog.rules'`.

- [ ] **Step 3: Реализация**

`backend/apps/catalog/rules.py`:
```python
"""Правила совместимости аксессуаров по характеристикам. Чистые функции, без БД."""

from collections.abc import Mapping

OPERATORS = {
    "eq": lambda device, target: device == target,
    "lte": lambda device, target: device <= target,
    "gte": lambda device, target: device >= target,
    "in": lambda device, target: device in target,
}


def validate_rule(conditions: object) -> list[str]:
    if not isinstance(conditions, list) or not conditions:
        return ["правило — непустой список условий"]
    errors = []
    for index, condition in enumerate(conditions, start=1):
        prefix = f"условие {index}"
        if not isinstance(condition, Mapping):
            errors.append(f"{prefix}: ожидается объект")
            continue
        if not isinstance(condition.get("attr"), str):
            errors.append(f"{prefix}: нужен attr")
        if condition.get("op") not in OPERATORS:
            errors.append(f"{prefix}: op — одно из {', '.join(OPERATORS)}")
        if ("value" in condition) == ("accessory_attr" in condition):
            errors.append(f"{prefix}: нужно ровно одно из value / accessory_attr")
    return errors


def rule_matches(
    conditions: list[Mapping], device_attrs: Mapping, accessory_attrs: Mapping
) -> bool:
    """Все условия выполняются: device[attr] OP (value | accessory[accessory_attr])."""
    for condition in conditions:
        device_value = device_attrs.get(condition["attr"])
        if "value" in condition:
            target = condition["value"]
        else:
            target = accessory_attrs.get(condition["accessory_attr"])
        if device_value is None or target is None:
            return False
        try:
            if not OPERATORS[condition["op"]](device_value, target):
                return False
        except TypeError:
            return False
    return True
```

В `backend/apps/catalog/models.py` добавить импорт:
```python
from .rules import validate_rule
```
и в конец файла:
```python


class AccessoryCompat(models.Model):
    accessory = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="compatible_devices"
    )
    device = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="explicit_accessories"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["accessory", "device"], name="unique_accessory_device")
        ]

    def __str__(self) -> str:
        return f"{self.accessory} → {self.device}"

    def clean(self) -> None:
        errors = {}
        if self.accessory_id and not self.accessory.is_accessory:
            errors["accessory"] = "Это не аксессуар"
        if self.device_id and self.device.is_accessory:
            errors["device"] = "Устройство не может быть аксессуаром"
        if errors:
            raise ValidationError(errors)


class CompatRule(models.Model):
    accessory = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="compat_rules"
    )
    conditions = models.JSONField(
        help_text='[{"attr": "charge_port", "op": "eq", "value": "usb-c"}, '
        '{"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"}]'
    )
    note = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"Правило для {self.accessory}"

    def clean(self) -> None:
        errors = validate_rule(self.conditions)
        if errors:
            raise ValidationError({"conditions": errors})
```

`backend/apps/catalog/compatibility.py`:
```python
"""Публичный сервис совместимости: явные привязки + правила."""

from django.db.models import QuerySet

from .models import AccessoryCompat, CompatRule, ProductModel, Status
from .rules import rule_matches


def is_compatible(accessory: ProductModel, device: ProductModel) -> bool:
    if AccessoryCompat.objects.filter(accessory=accessory, device=device).exists():
        return True
    return any(
        rule_matches(rule.conditions, device.attributes, accessory.attributes)
        for rule in accessory.compat_rules.all()
    )


def compatible_accessories(device: ProductModel) -> QuerySet[ProductModel]:
    ids = set(
        AccessoryCompat.objects.filter(device=device).values_list("accessory_id", flat=True)
    )
    rules = CompatRule.objects.select_related("accessory").filter(accessory__status=Status.ACTIVE)
    for rule in rules:
        if rule_matches(rule.conditions, device.attributes, rule.accessory.attributes):
            ids.add(rule.accessory_id)
    return ProductModel.objects.filter(
        pk__in=ids, status=Status.ACTIVE, is_accessory=True
    ).order_by("name_ru")
```

Run: `.venv/Scripts/python manage.py makemigrations catalog`
Expected: `0003_...py` с `AccessoryCompat`, `CompatRule`.

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/catalog`
Expected: `38 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add accessory compatibility by explicit links and rules"
```

---

### Task 6: Сравнение моделей

**Files:**
- Create: `backend/apps/catalog/comparison.py`
- Test: `backend/apps/catalog/tests/test_comparison.py`

**Interfaces:**
- Consumes: `Category.effective_attributes`, `Variant`, `ProductModel`.
- Produces: `CompareSpec(code, name, unit, comparison)`; `ComparisonRow(code, name, unit, values: tuple, best: tuple[int, ...])`; `best_indexes(values, direction) -> list[int]`; `build_comparison(specs, items) -> list[ComparisonRow]`; `compare_variants(variants, language="ru") -> list[ComparisonRow]` (`ValueError` при разных категориях или неизвестном языке).

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/catalog/tests/test_comparison.py`:
```python
import pytest

from apps.catalog.comparison import CompareSpec, best_indexes, build_comparison, compare_variants
from apps.catalog.models import Brand, Category, ProductModel


def test_higher_battery_wins():
    assert best_indexes([5000, 4000, 4500], "higher_better") == [0]


def test_lower_weight_wins():
    assert best_indexes([199, 170, 210], "lower_better") == [1]


def test_ties_highlight_all_winners():
    assert best_indexes([256, 512, 512], "higher_better") == [1, 2]


def test_all_equal_highlights_nothing():
    assert best_indexes([128, 128], "higher_better") == []


def test_missing_values_are_ignored():
    assert best_indexes([None, 4000, 5000], "higher_better") == [2]


def test_single_number_is_not_highlighted():
    assert best_indexes([None, 5], "higher_better") == []


def test_no_direction_no_highlight():
    assert best_indexes([1, 2], "none") == []


def test_build_comparison_skips_attributes_nobody_has():
    specs = [
        CompareSpec("battery_mah", "Батарея", "мА·ч", "higher_better"),
        CompareSpec("stylus", "Стилус", "", "none"),
    ]

    rows = build_comparison(specs, [{"battery_mah": 5000}, {"battery_mah": 4000}])

    assert [row.code for row in rows] == ["battery_mah"]
    assert rows[0].values == (5000, 4000)
    assert rows[0].best == (0,)


@pytest.mark.django_db
def test_compare_variants_merges_model_axes_and_variant_attributes(iphone, phones, make_variant):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(
        category=phones, brand=samsung, slug="galaxy-s26", name_ru="Galaxy S26",
        name_uz="Galaxy S26", attributes={"battery_mah": 5000},
    )
    a = make_variant(iphone, "IP-256", {"storage_gb": 256, "color": "black"}, attributes={"weight_g": 199})
    b = make_variant(galaxy, "S-512", {"storage_gb": 512, "color": "white"}, attributes={"weight_g": 220})
    a.save()
    b.save()

    rows = {row.code: row for row in compare_variants([a, b])}

    assert rows["battery_mah"].best == (1,)
    assert rows["storage_gb"].best == (1,)
    assert rows["weight_g"].best == (0,)
    assert rows["color"].best == ()
    assert rows["color"].values == ("black", "white")


@pytest.mark.django_db
def test_compare_variants_rejects_mixed_categories(iphone, apple, make_variant):
    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    case = ProductModel.objects.create(
        category=cases, brand=apple, slug="case", name_ru="Чехол", name_uz="G'ilof", is_accessory=True,
    )
    a = make_variant(iphone, "IP-256", {"storage_gb": 256, "color": "black"})
    b = make_variant(case, "CASE-1", {})
    a.save()
    b.save()

    with pytest.raises(ValueError):
        compare_variants([a, b])
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_comparison.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.catalog.comparison'`.

- [ ] **Step 3: Реализация**

`backend/apps/catalog/comparison.py`:
```python
"""Таблица сравнения с подсветкой лучших значений."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Variant


@dataclass(frozen=True)
class CompareSpec:
    code: str
    name: str
    unit: str
    comparison: str  # higher_better | lower_better | none


@dataclass(frozen=True)
class ComparisonRow:
    code: str
    name: str
    unit: str
    values: tuple
    best: tuple[int, ...]


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def best_indexes(values: Sequence, direction: str) -> list[int]:
    """Индексы лучших значений; пусто, если победителя нет."""
    if direction not in ("higher_better", "lower_better"):
        return []
    numeric = [(index, value) for index, value in enumerate(values) if _is_number(value)]
    if len(numeric) < 2:
        return []
    pick = max if direction == "higher_better" else min
    target = pick(value for _, value in numeric)
    winners = [index for index, value in numeric if value == target]
    return [] if len(winners) == len(numeric) else winners


def build_comparison(specs: Sequence[CompareSpec], items: Sequence[Mapping]) -> list[ComparisonRow]:
    rows = []
    for spec in specs:
        values = tuple(item.get(spec.code) for item in items)
        if all(value is None for value in values):
            continue
        best = tuple(best_indexes(values, spec.comparison))
        rows.append(ComparisonRow(spec.code, spec.name, spec.unit, values, best))
    return rows


def compare_variants(variants: Sequence[Variant], language: str = "ru") -> list[ComparisonRow]:
    if language not in ("ru", "uz"):
        raise ValueError("Язык: ru или uz")
    if not variants:
        return []
    if len({variant.product_model.category_id for variant in variants}) != 1:
        raise ValueError("Сравнивать можно только товары одной категории")
    category = variants[0].product_model.category
    specs = [
        CompareSpec(d.code, getattr(d, f"name_{language}"), d.unit, d.comparison)
        for d in category.effective_attributes()
    ]
    items = [
        {**variant.product_model.attributes, **variant.axes, **variant.attributes}
        for variant in variants
    ]
    return build_comparison(specs, items)
```

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/catalog`
Expected: `48 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add model comparison with best value highlighting"
```

---

### Task 7: Калькулятор цены в сумах

**Files:**
- Create: `backend/apps/pricing/__init__.py`, `backend/apps/pricing/apps.py`, `backend/apps/pricing/calculator.py`, `backend/apps/pricing/tests/__init__.py`
- Modify: `backend/config/settings.py` (INSTALLED_APPS)
- Test: `backend/apps/pricing/tests/test_calculator.py`

**Interfaces:**
- Produces: `PriceInputs(cost_usd: Decimal, rate: Decimal, markup_pct: Decimal, min_margin_uzs: int, rounding_step_uzs: int)`; `sale_price_uzs(inputs: PriceInputs) -> int` (= ceil(max(cost×rate×(1+markup/100), cost×rate+min_margin) / step) × step; `ValueError` на некорректный ввод); `needs_reprice(old_rate: Decimal, new_rate: Decimal, threshold_pct: Decimal = Decimal("0.5")) -> bool`.

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/pricing/tests/test_calculator.py`:
```python
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from apps.pricing.calculator import PriceInputs, needs_reprice, sale_price_uzs


def inputs(**overrides):
    values = dict(
        cost_usd=Decimal("1000"), rate=Decimal("12800"), markup_pct=Decimal("10"),
        min_margin_uzs=300_000, rounding_step_uzs=1000,
    )
    values.update(overrides)
    return PriceInputs(**values)


def test_markup_applied():
    # 1000 × 12 800 = 12 800 000; +10 % = 14 080 000
    assert sale_price_uzs(inputs()) == 14_080_000


def test_rounding_goes_up_to_step():
    # 999.99 × 12 800 × 1.1 = 14 079 859.2 → 14 080 000
    assert sale_price_uzs(inputs(cost_usd=Decimal("999.99"))) == 14_080_000


def test_min_margin_wins_over_small_markup():
    # 1 280 000 × 1.01 = 1 292 800 < 1 280 000 + 300 000
    assert sale_price_uzs(inputs(cost_usd=Decimal("100"), markup_pct=Decimal("1"))) == 1_580_000


@pytest.mark.parametrize(
    "field, value",
    [
        ("cost_usd", Decimal("0")),
        ("rate", Decimal("-1")),
        ("markup_pct", Decimal("-5")),
        ("min_margin_uzs", -1),
        ("rounding_step_uzs", 0),
    ],
)
def test_invalid_inputs_rejected(field, value):
    with pytest.raises(ValueError):
        sale_price_uzs(inputs(**{field: value}))


money = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("20000"), places=2)
rates = st.decimals(min_value=Decimal("1000"), max_value=Decimal("50000"), places=2)
percents = st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), places=2)
margins = st.integers(min_value=0, max_value=5_000_000)
steps = st.sampled_from([1, 100, 1000, 10_000])


@given(cost=money, rate=rates, markup=percents, margin=margins, step=steps)
def test_price_never_below_cost_plus_min_margin(cost, rate, markup, margin, step):
    price = sale_price_uzs(PriceInputs(cost, rate, markup, margin, step))

    assert price >= cost * rate + margin
    assert price % step == 0


@given(cost=money, rate=rates, markup=percents, margin=margins, step=steps)
def test_rounding_adds_less_than_one_step(cost, rate, markup, margin, step):
    price = sale_price_uzs(PriceInputs(cost, rate, markup, margin, step))
    raw = max(cost * rate * (1 + markup / 100), cost * rate + margin)

    assert price - raw < step


@given(cost=money, extra=money, rate=rates, markup=percents, margin=margins, step=steps)
def test_more_expensive_purchase_never_lowers_price(cost, extra, rate, markup, margin, step):
    cheap = sale_price_uzs(PriceInputs(cost, rate, markup, margin, step))
    pricey = sale_price_uzs(PriceInputs(cost + extra, rate, markup, margin, step))

    assert pricey >= cheap


def test_needs_reprice_only_above_threshold():
    assert not needs_reprice(Decimal("12800"), Decimal("12860"))  # +0.47 %
    assert needs_reprice(Decimal("12800"), Decimal("12870"))  # +0.55 %
    assert needs_reprice(Decimal("12800"), Decimal("12730"))  # −0.55 %
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/pricing`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pricing'`.

- [ ] **Step 3: Реализация**

`backend/apps/pricing/apps.py`:
```python
from django.apps import AppConfig


class PricingConfig(AppConfig):
    name = "apps.pricing"
```

В `backend/config/settings.py` добавить `"apps.pricing",` в `INSTALLED_APPS` после `"apps.catalog",`.

`backend/apps/pricing/calculator.py`:
```python
"""Расчёт цены продажи в сумах. Чистые функции, без БД."""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal


@dataclass(frozen=True)
class PriceInputs:
    cost_usd: Decimal
    rate: Decimal  # сумов за 1 USD с учётом спреда
    markup_pct: Decimal
    min_margin_uzs: int
    rounding_step_uzs: int


def sale_price_uzs(inputs: PriceInputs) -> int:
    """max(наценка, минимальная маржа), округление вверх до шага."""
    if inputs.cost_usd <= 0 or inputs.rate <= 0:
        raise ValueError("Закупка и курс должны быть положительными")
    if inputs.markup_pct < 0 or inputs.min_margin_uzs < 0:
        raise ValueError("Наценка и минимальная маржа не могут быть отрицательными")
    if inputs.rounding_step_uzs < 1:
        raise ValueError("Шаг округления — минимум 1 сум")
    cost_uzs = inputs.cost_usd * inputs.rate
    with_markup = cost_uzs * (1 + inputs.markup_pct / 100)
    floor = cost_uzs + inputs.min_margin_uzs
    raw = max(with_markup, floor)
    steps = (raw / inputs.rounding_step_uzs).to_integral_value(rounding=ROUND_CEILING)
    return int(steps) * inputs.rounding_step_uzs


def needs_reprice(
    old_rate: Decimal, new_rate: Decimal, threshold_pct: Decimal = Decimal("0.5")
) -> bool:
    """Пересчитывать цены, только если курс сдвинулся больше порога."""
    if old_rate <= 0:
        return True
    change_pct = abs(new_rate - old_rate) / old_rate * 100
    return change_pct > threshold_pct
```

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/pricing`
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add UZS price calculator with property-based tests"
```

---

### Task 8: Курс ЦБ и правила наценки

**Files:**
- Create: `backend/apps/pricing/models.py`, `backend/apps/pricing/markup.py`, `backend/apps/pricing/cbu.py`, `backend/apps/pricing/management/__init__.py`, `backend/apps/pricing/management/commands/__init__.py`, `backend/apps/pricing/management/commands/fetch_cbu_rate.py`
- Test: `backend/apps/pricing/tests/test_markup.py`, `backend/apps/pricing/tests/test_cbu.py`

**Interfaces:**
- Consumes: `PriceInputs`, `sale_price_uzs`, `Category.lineage`, `Variant`, `Brand`.
- Produces: `ExchangeRate(date, cbu_rate, spread_pct)` + свойство `effective_rate -> Decimal`; `MarkupRule(variant | category | brand | глобальное, markup_pct, min_margin_uzs, rounding_step_uzs, is_active)`; `resolve_markup_rule(variant) -> MarkupRule` (вариант → ближайшая категория → бренд → глобальное; `MarkupRule.DoesNotExist`, если нет ни одного); `price_for(variant, cost_usd: Decimal, rate: ExchangeRate) -> int`; `parse_usd_rate(payload) -> tuple[date, Decimal]`; `fetch_usd_rate(day, http_get=requests.get) -> tuple[date, Decimal]`; команда `manage.py fetch_cbu_rate`.

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/pricing/tests/test_markup.py`:
```python
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.catalog.models import Category
from apps.pricing.markup import price_for, resolve_markup_rule
from apps.pricing.models import ExchangeRate, MarkupRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def variant(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", {"storage_gb": 256, "color": "black"})
    variant.save()
    return variant


def rule(**kwargs):
    kwargs.setdefault("markup_pct", Decimal("10"))
    return MarkupRule.objects.create(**kwargs)


def test_effective_rate_adds_spread():
    rate = ExchangeRate(date=date(2026, 10, 8), cbu_rate=Decimal("12800"), spread_pct=Decimal("1"))

    assert rate.effective_rate == Decimal("12928.00")


def test_variant_rule_beats_category_rule(variant, phones):
    rule(category=phones, markup_pct=Decimal("8"))
    specific = rule(variant=variant, markup_pct=Decimal("5"))

    assert resolve_markup_rule(variant) == specific


def test_nearest_category_beats_parent(variant, phones):
    electronics = Category.objects.create(slug="electronics", name_ru="Электроника", name_uz="Elektronika")
    phones.parent = electronics
    phones.save()
    rule(category=electronics, markup_pct=Decimal("15"))
    nearest = rule(category=phones, markup_pct=Decimal("8"))

    assert resolve_markup_rule(variant) == nearest


def test_brand_rule_then_global_fallback(variant, apple):
    global_rule = rule()
    assert resolve_markup_rule(variant) == global_rule

    brand_rule = rule(brand=apple, markup_pct=Decimal("7"))
    assert resolve_markup_rule(variant) == brand_rule


def test_inactive_rules_are_ignored(variant, phones):
    rule(category=phones, is_active=False)

    with pytest.raises(MarkupRule.DoesNotExist):
        resolve_markup_rule(variant)


def test_rule_with_two_scopes_is_invalid(variant, phones):
    invalid = MarkupRule(variant=variant, category=phones, markup_pct=Decimal("5"))

    with pytest.raises(ValidationError):
        invalid.full_clean()


def test_only_one_active_global_rule():
    rule()

    with pytest.raises(IntegrityError):
        rule()


def test_price_for_uses_rule_and_effective_rate(variant, phones):
    rule(category=phones, markup_pct=Decimal("10"), min_margin_uzs=0, rounding_step_uzs=1000)
    rate = ExchangeRate.objects.create(
        date=date(2026, 10, 8), cbu_rate=Decimal("12800"), spread_pct=Decimal("1")
    )

    # 1000 × 12 928 × 1.1 = 14 220 800 → 14 221 000
    assert price_for(variant, Decimal("1000"), rate) == 14_221_000
```

`backend/apps/pricing/tests/test_cbu.py`:
```python
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.pricing.cbu import CBU_URL, fetch_usd_rate, parse_usd_rate
from apps.pricing.models import ExchangeRate

SAMPLE = [
    {
        "id": 69, "Code": "840", "Ccy": "USD", "CcyNm_RU": "Доллар США", "Nominal": "1",
        "Rate": "12850.55", "Diff": "-10.01", "Date": "07.10.2026",
    }
]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self.payload


def test_parse_usd_rate():
    assert parse_usd_rate(SAMPLE) == (date(2026, 10, 7), Decimal("12850.55"))


def test_parse_divides_by_nominal():
    payload = [dict(SAMPLE[0], Nominal="10", Rate="128505.50")]

    assert parse_usd_rate(payload) == (date(2026, 10, 7), Decimal("12850.55"))


def test_parse_without_usd_fails():
    with pytest.raises(ValueError):
        parse_usd_rate([dict(SAMPLE[0], Ccy="EUR")])


def test_fetch_requests_dated_url():
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse(SAMPLE)

    result = fetch_usd_rate(date(2026, 10, 7), http_get=fake_get)

    assert result == (date(2026, 10, 7), Decimal("12850.55"))
    assert calls == [(CBU_URL.format(day="2026-10-07"), 10)]


def test_fetch_raises_on_http_error():
    with pytest.raises(RuntimeError):
        fetch_usd_rate(date(2026, 10, 7), http_get=lambda url, timeout: FakeResponse([], status=503))


@pytest.mark.django_db
def test_command_upserts_rate_and_keeps_spread(monkeypatch):
    ExchangeRate.objects.create(date=date(2026, 10, 7), cbu_rate=Decimal("1"), spread_pct=Decimal("2"))
    monkeypatch.setattr(
        "apps.pricing.management.commands.fetch_cbu_rate.fetch_usd_rate",
        lambda day: (date(2026, 10, 7), Decimal("12850.55")),
    )

    call_command("fetch_cbu_rate")

    rate = ExchangeRate.objects.get(date=date(2026, 10, 7))
    assert rate.cbu_rate == Decimal("12850.55")
    assert rate.spread_pct == Decimal("2")
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/pricing`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pricing.markup'`.

- [ ] **Step 3: Реализация**

`backend/apps/pricing/models.py`:
```python
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
```

`backend/apps/pricing/markup.py`:
```python
"""Публичный сервис цен: выбор правила наценки и цена варианта."""

from decimal import Decimal

from apps.catalog.models import Variant

from .calculator import PriceInputs, sale_price_uzs
from .models import ExchangeRate, MarkupRule


def resolve_markup_rule(variant: Variant) -> MarkupRule:
    """Вариант → ближайшая категория → бренд → глобальное правило."""
    active = MarkupRule.objects.filter(is_active=True)
    rule = active.filter(variant=variant).first()
    if rule:
        return rule
    for category in reversed(variant.product_model.category.lineage()):
        rule = active.filter(category=category).first()
        if rule:
            return rule
    rule = active.filter(brand_id=variant.product_model.brand_id).first()
    if rule:
        return rule
    rule = active.filter(variant__isnull=True, category__isnull=True, brand__isnull=True).first()
    if rule:
        return rule
    raise MarkupRule.DoesNotExist("Нет активного правила наценки, даже общего")


def price_for(variant: Variant, cost_usd: Decimal, rate: ExchangeRate) -> int:
    rule = resolve_markup_rule(variant)
    return sale_price_uzs(
        PriceInputs(
            cost_usd=cost_usd,
            rate=rate.effective_rate,
            markup_pct=rule.markup_pct,
            min_margin_uzs=rule.min_margin_uzs,
            rounding_step_uzs=rule.rounding_step_uzs,
        )
    )
```

`backend/apps/pricing/cbu.py`:
```python
"""Курс USD Центрального банка Узбекистана (cbu.uz)."""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import requests

CBU_URL = "https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/{day}/"


def parse_usd_rate(payload: object) -> tuple[date, Decimal]:
    if not isinstance(payload, list):
        raise ValueError("Неожиданный ответ ЦБ")
    for item in payload:
        if isinstance(item, dict) and item.get("Ccy") == "USD":
            rate = Decimal(item["Rate"]) / Decimal(item.get("Nominal") or "1")
            day = datetime.strptime(item["Date"], "%d.%m.%Y").date()
            return day, rate.quantize(Decimal("0.01"))
    raise ValueError("В ответе ЦБ нет курса USD")


def fetch_usd_rate(
    day: date, http_get: Callable[..., requests.Response] = requests.get
) -> tuple[date, Decimal]:
    response = http_get(CBU_URL.format(day=day.isoformat()), timeout=10)
    response.raise_for_status()
    return parse_usd_rate(response.json())
```

`backend/apps/pricing/management/__init__.py`, `backend/apps/pricing/management/commands/__init__.py` — пустые.

`backend/apps/pricing/management/commands/fetch_cbu_rate.py`:
```python
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.pricing.cbu import fetch_usd_rate
from apps.pricing.models import ExchangeRate


class Command(BaseCommand):
    help = "Загрузить курс USD ЦБ Узбекистана на сегодня"

    def handle(self, *args, **options) -> None:
        rate_date, rate = fetch_usd_rate(timezone.localdate())
        obj, created = ExchangeRate.objects.update_or_create(
            date=rate_date, defaults={"cbu_rate": rate}
        )
        action = "Создан" if created else "Обновлён"
        self.stdout.write(f"{action} курс на {obj.date}: {obj.cbu_rate}")
```

Run: `.venv/Scripts/python manage.py makemigrations pricing`
Expected: `0001_initial.py` с `ExchangeRate`, `MarkupRule`.

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/pricing`
Expected: `26 passed`.

- [ ] **Step 5: Проверить реальный ответ ЦБ**

Run: `curl -s https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/2026-10-07/`
Expected: JSON-массив с ключами `Ccy`, `Rate`, `Nominal`, `Date`. Если формат отличается — поправить `SAMPLE` и `parse_usd_rate`, повторить Step 4.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: add CBU exchange rate and markup rules"
```

---

### Task 9: Бюджет и правила подарков

**Files:**
- Create: `backend/apps/promo/__init__.py`, `backend/apps/promo/apps.py`, `backend/apps/promo/budget.py`, `backend/apps/promo/models.py`, `backend/apps/promo/selection.py`, `backend/apps/promo/tests/__init__.py`
- Modify: `backend/config/settings.py` (INSTALLED_APPS)
- Test: `backend/apps/promo/tests/test_budget.py`, `backend/apps/promo/tests/test_selection.py`

**Interfaces:**
- Consumes: `Category.lineage`, `Variant`, `Brand`.
- Produces: `gift_budget_uzs(price_uzs: int, cost_uzs: int, commission_pct: Decimal, budget_pct: Decimal, cap_uzs: int) -> int`; `GiftPolicy` (поля из спецификации 2.1 + `name`, `is_active`); `select_gift_policy(variant, price_uzs: int, at: datetime | None = None) -> GiftPolicy | None` (наибольший `priority`, при равенстве — более новая).

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/promo/tests/test_budget.py`:
```python
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from apps.promo.budget import gift_budget_uzs


def test_budget_is_share_of_net_margin():
    # маржа 1 280 000, 10 % = 128 000 < потолка 150 000
    assert gift_budget_uzs(14_080_000, 12_800_000, Decimal("0"), Decimal("10"), 150_000) == 128_000


def test_installment_commission_shrinks_budget():
    # комиссия 5 % = 704 000 → маржа 576 000 → 57 600
    assert gift_budget_uzs(14_080_000, 12_800_000, Decimal("5"), Decimal("10"), 150_000) == 57_600


def test_cap_limits_budget():
    assert gift_budget_uzs(14_080_000, 12_800_000, Decimal("0"), Decimal("50"), 150_000) == 150_000


def test_no_margin_no_gift():
    assert gift_budget_uzs(10_000_000, 10_500_000, Decimal("0"), Decimal("10"), 150_000) == 0


def test_negative_input_rejected():
    with pytest.raises(ValueError):
        gift_budget_uzs(-1, 0, Decimal("0"), Decimal("10"), 150_000)


prices = st.integers(min_value=0, max_value=100_000_000)
percents = st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), places=2)
caps = st.integers(min_value=0, max_value=1_000_000)


@given(price=prices, cost=prices, commission=percents, share=percents, cap=caps)
def test_budget_bounds(price, cost, commission, share, cap):
    budget = gift_budget_uzs(price, cost, commission, share, cap)
    net_margin = Decimal(price) - cost - Decimal(price) * commission / 100

    assert 0 <= budget <= cap
    assert budget <= max(net_margin, 0) * share / 100


@given(price=prices, cost=prices, low=percents, extra=percents, share=percents, cap=caps)
def test_higher_commission_never_increases_budget(price, cost, low, extra, share, cap):
    cheap = gift_budget_uzs(price, cost, low, share, cap)
    expensive = gift_budget_uzs(price, cost, low + extra, share, cap)

    assert expensive <= cheap
```

`backend/apps/promo/tests/test_selection.py`:
```python
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalog.models import Brand, Category
from apps.promo.models import GiftPolicy
from apps.promo.selection import select_gift_policy

pytestmark = pytest.mark.django_db


@pytest.fixture
def variant(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", {"storage_gb": 256, "color": "black"})
    variant.save()
    return variant


def policy(name, **kwargs):
    kwargs.setdefault("budget_pct_of_net_margin", Decimal("10"))
    kwargs.setdefault("budget_cap_uzs", 150_000)
    return GiftPolicy.objects.create(name=name, **kwargs)


def test_highest_priority_wins(variant, phones):
    policy("общая")
    best = policy("смартфоны", category=phones, priority=10)

    assert select_gift_policy(variant, 14_000_000) == best


def test_parent_category_policy_applies_to_child(variant, phones):
    electronics = Category.objects.create(slug="electronics", name_ru="Электроника", name_uz="Elektronika")
    phones.parent = electronics
    phones.save()
    parent_policy = policy("электроника", category=electronics)

    assert select_gift_policy(variant, 14_000_000) == parent_policy


def test_other_brand_policy_is_skipped(variant):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    policy("samsung", brand=samsung, priority=10)
    fallback = policy("общая")

    assert select_gift_policy(variant, 14_000_000) == fallback


def test_price_range_is_respected(variant):
    policy("дорогие", min_price_uzs=20_000_000, priority=10)
    regular = policy("до 20 млн", max_price_uzs=20_000_000)

    assert select_gift_policy(variant, 14_000_000) == regular


def test_expired_and_future_policies_are_skipped(variant):
    now = timezone.now()
    policy("прошлая", active_to=now - timedelta(days=1), priority=10)
    policy("будущая", active_from=now + timedelta(days=1), priority=10)
    current = policy("текущая", active_from=now - timedelta(days=1), active_to=now + timedelta(days=1))

    assert select_gift_policy(variant, 14_000_000, at=now) == current


def test_inactive_policy_and_no_match_give_none(variant):
    policy("выключена", is_active=False)

    assert select_gift_policy(variant, 14_000_000) is None


def test_policy_rejects_inverted_ranges():
    invalid = GiftPolicy(
        name="x", budget_pct_of_net_margin=Decimal("10"), budget_cap_uzs=1,
        min_price_uzs=10, max_price_uzs=5,
    )

    with pytest.raises(ValidationError) as exc:
        invalid.full_clean()

    assert "max_price_uzs" in exc.value.message_dict
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/promo`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.promo'`.

- [ ] **Step 3: Реализация**

`backend/apps/promo/apps.py`:
```python
from django.apps import AppConfig


class PromoConfig(AppConfig):
    name = "apps.promo"
```

В `backend/config/settings.py` добавить `"apps.promo",` в `INSTALLED_APPS` после `"apps.pricing",`.

`backend/apps/promo/budget.py`:
```python
"""Бюджет подарка. Чистые функции, без БД."""

from decimal import ROUND_FLOOR, Decimal


def gift_budget_uzs(
    price_uzs: int, cost_uzs: int, commission_pct: Decimal, budget_pct: Decimal, cap_uzs: int
) -> int:
    """Доля чистой маржи (после комиссии оплаты или рассрочки), не больше потолка."""
    if min(price_uzs, cost_uzs, cap_uzs) < 0 or commission_pct < 0 or budget_pct < 0:
        raise ValueError("Входные данные не могут быть отрицательными")
    commission = Decimal(price_uzs) * commission_pct / 100
    net_margin = Decimal(price_uzs) - cost_uzs - commission
    if net_margin <= 0:
        return 0
    budget = (net_margin * budget_pct / 100).to_integral_value(rounding=ROUND_FLOOR)
    return int(min(budget, cap_uzs))
```

`backend/apps/promo/models.py`:
```python
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
        verbose_name_plural = "gift policies"

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
```

`backend/apps/promo/selection.py`:
```python
"""Публичный сервис: какое правило подарка действует для варианта."""

from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Variant

from .models import GiftPolicy


def select_gift_policy(
    variant: Variant, price_uzs: int, at: datetime | None = None
) -> GiftPolicy | None:
    at = at or timezone.now()
    product = variant.product_model
    category_ids = [category.pk for category in product.category.lineage()]
    return (
        GiftPolicy.objects.filter(is_active=True)
        .filter(Q(category__isnull=True) | Q(category_id__in=category_ids))
        .filter(Q(brand__isnull=True) | Q(brand_id=product.brand_id))
        .filter(Q(min_price_uzs__isnull=True) | Q(min_price_uzs__lte=price_uzs))
        .filter(Q(max_price_uzs__isnull=True) | Q(max_price_uzs__gte=price_uzs))
        .filter(Q(active_from__isnull=True) | Q(active_from__lte=at))
        .filter(Q(active_to__isnull=True) | Q(active_to__gt=at))
        .order_by("-priority", "-pk")
        .first()
    )
```

Run: `.venv/Scripts/python manage.py makemigrations promo`
Expected: `0001_initial.py` с `GiftPolicy`.

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest apps/promo`
Expected: `14 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add gift budget and gift policy selection"
```

---

### Task 10: Админка

**Files:**
- Create: `backend/apps/catalog/admin.py`, `backend/apps/pricing/admin.py`, `backend/apps/promo/admin.py`
- Test: `backend/apps/core/tests/test_admin.py`

**Interfaces:**
- Consumes: все модели Task 2–9.
- Produces: страницы Django Admin для каталога, курсов, наценок и подарков; варианты, явные привязки и правила совместимости — инлайны в карточке модели товара.

- [ ] **Step 1: Написать падающий тест**

`backend/apps/core/tests/test_admin.py`:
```python
import pytest
from django.urls import reverse

MODELS = [
    "catalog.category",
    "catalog.brand",
    "catalog.productmodel",
    "catalog.variant",
    "pricing.exchangerate",
    "pricing.markuprule",
    "promo.giftpolicy",
]


@pytest.mark.django_db
@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("page", ["changelist", "add"])
def test_admin_pages_open(admin_client, model, page):
    app_label, model_name = model.split(".")

    response = admin_client.get(reverse(f"admin:{app_label}_{model_name}_{page}"))

    assert response.status_code == 200
```

- [ ] **Step 2: Запустить — тест падает**

Run: `.venv/Scripts/python -m pytest apps/core/tests/test_admin.py`
Expected: FAIL — `NoReverseMatch: Reverse for 'catalog_category_changelist' not found`.

- [ ] **Step 3: Реализация**

`backend/apps/catalog/admin.py`:
```python
from django.contrib import admin

from .models import (
    AccessoryCompat,
    AttributeDefinition,
    Brand,
    Category,
    CompatRule,
    ProductModel,
    Variant,
)


class AttributeDefinitionInline(admin.TabularInline):
    model = AttributeDefinition
    extra = 0
    fields = (
        "code", "name_ru", "name_uz", "type", "unit", "enum_values", "level",
        "is_variant_axis", "is_required", "is_facet", "comparison", "sort_order",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "slug", "parent", "is_serialized")
    search_fields = ("name_ru", "name_uz", "slug")
    inlines = [AttributeDefinitionInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class VariantInline(admin.StackedInline):
    model = Variant
    extra = 0
    fields = (
        "sku", "axes", "attributes", "mxik_code", "package_code", "barcodes",
        "weight_g", "images", "giftable", "status",
    )


class AccessoryCompatInline(admin.TabularInline):
    model = AccessoryCompat
    fk_name = "accessory"
    extra = 0
    autocomplete_fields = ("device",)
    verbose_name_plural = "Совместимые устройства (явно)"


class CompatRuleInline(admin.TabularInline):
    model = CompatRule
    extra = 0
    verbose_name_plural = "Правила совместимости"


@admin.register(ProductModel)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "brand", "category", "is_accessory", "status")
    list_filter = ("status", "is_accessory", "category", "brand")
    search_fields = ("name_ru", "name_uz", "slug")
    autocomplete_fields = ("category", "brand")
    inlines = [VariantInline, AccessoryCompatInline, CompatRuleInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product_model", "status", "giftable")
    list_filter = ("status", "giftable")
    search_fields = ("sku", "product_model__name_ru")
    autocomplete_fields = ("product_model",)
```

`backend/apps/pricing/admin.py`:
```python
from django.contrib import admin

from .models import ExchangeRate, MarkupRule


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("date", "cbu_rate", "spread_pct", "effective_rate")
    date_hierarchy = "date"


@admin.register(MarkupRule)
class MarkupRuleAdmin(admin.ModelAdmin):
    list_display = ("__str__", "markup_pct", "min_margin_uzs", "rounding_step_uzs", "is_active")
    list_filter = ("is_active",)
    autocomplete_fields = ("variant", "category", "brand")
```

`backend/apps/promo/admin.py`:
```python
from django.contrib import admin

from .models import GiftPolicy


@admin.register(GiftPolicy)
class GiftPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "brand", "budget_pct_of_net_margin", "budget_cap_uzs",
        "priority", "is_active",
    )
    list_filter = ("is_active",)
    autocomplete_fields = ("category", "brand")
```

- [ ] **Step 4: Запустить — тесты проходят**

Run: `.venv/Scripts/python -m pytest`
Expected: все тесты проекта проходят (`14 passed` в `test_admin.py`).

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add admin for catalog, pricing and gift policies"
```

---

### Task 11: Публичное API каталога

**Files:**
- Create: `backend/apps/catalog/serializers.py`, `backend/apps/catalog/views.py`, `backend/apps/catalog/urls.py`
- Modify: `backend/apps/catalog/models.py` (`Category.subtree_ids`), `backend/config/urls.py`
- Test: `backend/apps/catalog/tests/test_api.py`

**Interfaces:**
- Consumes: `compatible_accessories`, `compare_variants`.
- Produces (все `AllowAny`, только GET):
  - `GET /api/v1/catalog/categories/` → список категорий без пагинации;
  - `GET /api/v1/catalog/products/?category=<slug>` → активные модели, включая подкатегории, пагинация `{"count", "next", "previous", "results"}`;
  - `GET /api/v1/catalog/products/<slug>/` → модель + активные варианты (без `mxik_code`/`package_code`);
  - `GET /api/v1/catalog/products/<slug>/accessories/` → совместимые аксессуары;
  - `GET /api/v1/catalog/compare/?skus=A,B[&lang=uz]` → строки сравнения; 400 при < 2 или > 4 SKU, неизвестных SKU, разных категориях.
  - `Category.subtree_ids() -> set[int]`.

- [ ] **Step 1: Написать падающие тесты**

`backend/apps/catalog/tests/test_api.py`:
```python
import pytest

from apps.catalog.models import AccessoryCompat, Brand, Category, ProductModel, Status

pytestmark = pytest.mark.django_db

BASE = "/api/v1/catalog"


@pytest.fixture
def catalog(iphone, phones, make_variant):
    make_variant(iphone, "IP-256-B", {"storage_gb": 256, "color": "black"},
                 attributes={"weight_g": 199}, status=Status.ACTIVE).save()
    make_variant(iphone, "IP-512-W", {"storage_gb": 512, "color": "white"},
                 attributes={"weight_g": 199}, status=Status.DRAFT).save()
    return iphone


def test_categories_are_public(phones, client):
    response = client.get(f"{BASE}/categories/")

    assert response.status_code == 200
    assert [c["slug"] for c in response.json()] == ["phones"]


def test_product_list_includes_subcategories_and_hides_drafts(catalog, phones, apple, client):
    flagships = Category.objects.create(slug="flagships", name_ru="Флагманы", name_uz="Flagmanlar", parent=phones)
    ProductModel.objects.create(category=flagships, brand=apple, slug="iphone-17-pro",
                                name_ru="iPhone 17 Pro", name_uz="iPhone 17 Pro", status=Status.ACTIVE)
    ProductModel.objects.create(category=phones, brand=apple, slug="draft-phone",
                                name_ru="Черновик", name_uz="Qoralama")

    response = client.get(f"{BASE}/products/", {"category": "phones"})

    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()["results"]]
    assert slugs == ["iphone-16-pro", "iphone-17-pro"]


def test_product_detail_shows_active_variants_without_fiscal_codes(catalog, client):
    response = client.get(f"{BASE}/products/iphone-16-pro/")

    assert response.status_code == 200
    body = response.json()
    assert [v["sku"] for v in body["variants"]] == ["IP-256-B"]
    assert "mxik_code" not in body["variants"][0]
    assert body["brand"]["name"] == "Apple"


def test_unknown_product_is_404(client, db):
    assert client.get(f"{BASE}/products/nope/").status_code == 404


def test_accessories_endpoint(catalog, apple, client):
    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    case = ProductModel.objects.create(category=cases, brand=apple, slug="case-16-pro",
                                       name_ru="Чехол 16 Pro", name_uz="G'ilof 16 Pro",
                                       is_accessory=True, status=Status.ACTIVE)
    AccessoryCompat.objects.create(accessory=case, device=catalog)

    response = client.get(f"{BASE}/products/iphone-16-pro/accessories/")

    assert [p["slug"] for p in response.json()["results"]] == ["case-16-pro"]


def test_compare_returns_rows_with_best(catalog, phones, make_variant, client):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(category=phones, brand=samsung, slug="galaxy-s26",
                                         name_ru="Galaxy S26", name_uz="Galaxy S26",
                                         attributes={"battery_mah": 5000}, status=Status.ACTIVE)
    make_variant(galaxy, "S26-256", {"storage_gb": 256, "color": "black"},
                 attributes={"weight_g": 220}, status=Status.ACTIVE).save()

    response = client.get(f"{BASE}/compare/", {"skus": "IP-256-B,S26-256"})

    assert response.status_code == 200
    rows = {row["code"]: row for row in response.json()}
    assert rows["battery_mah"]["best"] == [1]
    assert rows["weight_g"]["best"] == [0]


@pytest.mark.parametrize("skus", ["IP-256-B", "IP-256-B,NOPE", "A,B,C,D,E"])
def test_compare_rejects_bad_requests(catalog, client, skus):
    assert client.get(f"{BASE}/compare/", {"skus": skus}).status_code == 400


def test_api_is_read_only(catalog, client):
    assert client.post(f"{BASE}/products/", {}).status_code in (403, 405)
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `.venv/Scripts/python -m pytest apps/catalog/tests/test_api.py`
Expected: FAIL — 404 на всех эндпоинтах (маршрутов нет).

- [ ] **Step 3: Реализация**

В `backend/apps/catalog/models.py` добавить метод в `Category` (после `lineage`):
```python
    def subtree_ids(self) -> set[int]:
        """pk этой категории и всех её потомков."""
        ids = {self.pk}
        frontier = [self.pk]
        while frontier:
            frontier = list(
                Category.objects.filter(parent_id__in=frontier)
                .exclude(pk__in=ids)
                .values_list("pk", flat=True)
            )
            ids.update(frontier)
        return ids
```

`backend/apps/catalog/serializers.py`:
```python
from rest_framework import serializers

from .models import Brand, Category, ProductModel, Status, Variant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name_ru", "name_uz", "parent", "is_serialized"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["slug", "name"]


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ["sku", "axes", "attributes", "images", "giftable"]


class ProductListSerializer(serializers.ModelSerializer):
    brand = BrandSerializer()
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = ProductModel
        fields = ["slug", "name_ru", "name_uz", "brand", "category", "is_accessory"]


class ProductDetailSerializer(ProductListSerializer):
    variants = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description_ru", "description_uz", "attributes",
            "seo_title_ru", "seo_title_uz", "seo_description_ru", "seo_description_uz",
            "variants",
        ]

    def get_variants(self, obj: ProductModel) -> list[dict]:
        active = [variant for variant in obj.variants.all() if variant.status == Status.ACTIVE]
        return VariantSerializer(active, many=True).data


class ComparisonRowSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()
    values = serializers.ListField(child=serializers.JSONField())
    best = serializers.ListField(child=serializers.IntegerField())
```

`backend/apps/catalog/views.py`:
```python
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .comparison import compare_variants
from .compatibility import compatible_accessories
from .models import Category, ProductModel, Status, Variant
from .serializers import (
    CategorySerializer,
    ComparisonRowSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)

MAX_COMPARE = 4


class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = Category.objects.order_by("pk")


class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        queryset = (
            ProductModel.objects.filter(status=Status.ACTIVE)
            .select_related("brand", "category")
            .order_by("name_ru")
        )
        slug = self.request.query_params.get("category")
        if slug:
            category = get_object_or_404(Category, slug=slug)
            queryset = queryset.filter(category_id__in=category.subtree_ids())
        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
    queryset = (
        ProductModel.objects.filter(status=Status.ACTIVE)
        .select_related("brand", "category")
        .prefetch_related("variants")
    )


class AccessoriesView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        device = get_object_or_404(ProductModel, slug=self.kwargs["slug"], status=Status.ACTIVE)
        return compatible_accessories(device).select_related("brand", "category")


class CompareView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        skus = [sku for sku in request.query_params.get("skus", "").split(",") if sku]
        if not 2 <= len(skus) <= MAX_COMPARE:
            raise ValidationError({"skus": f"Укажите от 2 до {MAX_COMPARE} SKU через запятую"})
        found = {
            variant.sku: variant
            for variant in Variant.objects.filter(sku__in=skus, status=Status.ACTIVE)
            .select_related("product_model__category")
        }
        missing = [sku for sku in skus if sku not in found]
        if missing:
            raise ValidationError({"skus": f"Не найдены: {', '.join(missing)}"})
        try:
            rows = compare_variants(
                [found[sku] for sku in skus], language=request.query_params.get("lang", "ru")
            )
        except ValueError as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(ComparisonRowSerializer(rows, many=True).data)
```

`backend/apps/catalog/urls.py`:
```python
from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="categories"),
    path("products/", views.ProductListView.as_view(), name="products"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path(
        "products/<slug:slug>/accessories/",
        views.AccessoriesView.as_view(),
        name="product-accessories",
    ),
    path("compare/", views.CompareView.as_view(), name="compare"),
]
```

В `backend/config/urls.py` добавить в `urlpatterns`:
```python
    path("api/v1/catalog/", include("apps.catalog.urls")),
```

- [ ] **Step 4: Запустить — все тесты проходят**

Run: `.venv/Scripts/python -m pytest`
Expected: все тесты проекта проходят, 0 failed.

- [ ] **Step 5: Проверка миграций и системных проверок**

Run: `SECRET_KEY=dev .venv/Scripts/python manage.py makemigrations --check --dry-run && SECRET_KEY=dev .venv/Scripts/python manage.py check`
Expected: `No changes detected` и `System check identified no issues`.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: add public read-only catalog API"
```

---

## Следующие планы (не входят в этот)

- **План 2. Поставщики и остатки:** Supplier, коннекторы (Excel/Sheets, API), SupplierFeedRow, очередь сопоставления, Offer, InventoryUnit (IMEI), Reservation, PriceSnapshot и пересчёт цен по курсу (Celery + Redis), GIN-индексы и прогон тестов на PostgreSQL.
- **План 3. Поиск и витрина:** Meilisearch (автокомплит, транслитерация, фасеты), OpenAPI (drf-spectacular) и TypeScript-клиент, Next.js (каталог, карточка, сравнение), тема Unfold для админки.
- **План 4. Продажа:** корзина, чекаут, OTP, машина состояний заказа, outbox, Payme/Click, Telegram-бот, доставка, подарок в заказе.
- **План 5. Операции и рассрочка:** приёмка и сборка с IMEI, рассрочка, рабочее место оператора, личный кабинет, CI/CD и staging.
