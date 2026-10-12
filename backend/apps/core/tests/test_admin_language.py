"""Админку смотрят ученики и сотрудники — меню и заголовки по-русски."""

import re

import pytest
from django.contrib import admin

pytestmark = pytest.mark.django_db
CYRILLIC = re.compile(r"[а-яё]", re.IGNORECASE)


def test_every_admin_section_has_a_russian_name():
    english = [
        f"{model._meta.app_label}: {model._meta.verbose_name_plural}"
        for model in admin.site._registry
        if model._meta.app_label != "auth" and not CYRILLIC.search(str(model._meta.verbose_name_plural))
    ]
    english += [
        f"раздел {model._meta.app_config.label}: {model._meta.app_config.verbose_name}"
        for model in admin.site._registry
        if model._meta.app_label != "auth" and not CYRILLIC.search(str(model._meta.app_config.verbose_name))
    ]
    assert english == []


def test_admin_index_names_the_shop(admin_client):
    page = admin_client.get("/admin/").content.decode()

    assert "Sovgʻa" in page and "Администрирование Django" not in page
    assert all(name in page for name in ("Каталог", "Товары", "Склад", "Поставщики", "Заказы", "Платежи"))
