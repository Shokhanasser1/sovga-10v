"""Магазин из тестов заказов + готовый подтверждённый заказ для оплаты."""

import pytest
from django.utils import timezone

from apps.customers.services import customer_for_phone
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, create_order
from apps.orders.tests.conftest import shop  # noqa: F401 — фикстура магазина

NOW = timezone.now()


@pytest.fixture
def order(shop):  # noqa: F811
    customer = customer_for_phone("+998901234567")
    return create_order(
        customer, [CartItem("IP16P-256-B", 1, gift_sku="CASE-1")], "card", DeliveryAddress("Ташкент"), "", NOW
    )
