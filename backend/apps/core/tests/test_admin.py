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
