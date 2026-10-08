import pytest
from django.urls import reverse

EDITABLE = [
    "catalog.category",
    "catalog.brand",
    "catalog.productmodel",
    "catalog.variant",
    "pricing.exchangerate",
    "pricing.markuprule",
    "promo.giftpolicy",
    "sourcing.supplier",
    "sourcing.warehouse",
    "sourcing.offer",
    "sourcing.supplierskumap",
    "inventory.purchasebatch",
    "inventory.inventoryunit",
]
READ_ONLY = [
    "sourcing.supplierfeedrun",
    "sourcing.supplierfeedrow",
    "sourcing.reservation",
    "pricing.pricesnapshot",
    "customers.customer",
    "customers.otpcode",
    "orders.order",
    "notifications.outboxevent",
]


def open_page(admin_client, model, page):
    app_label, model_name = model.split(".")
    return admin_client.get(reverse(f"admin:{app_label}_{model_name}_{page}"))


@pytest.mark.django_db
@pytest.mark.parametrize("model", EDITABLE + READ_ONLY)
def test_changelist_opens(admin_client, model):
    assert open_page(admin_client, model, "changelist").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("model", EDITABLE)
def test_add_page_opens(admin_client, model):
    assert open_page(admin_client, model, "add").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("model", READ_ONLY)
def test_generated_records_cannot_be_added_by_hand(admin_client, model):
    assert open_page(admin_client, model, "add").status_code == 403
