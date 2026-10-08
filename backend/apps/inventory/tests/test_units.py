from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import Category, ProductModel
from apps.inventory.models import InventoryUnit
from apps.inventory.services import receive_unit, sync_own_offer
from apps.sourcing.models import Offer

pytestmark = pytest.mark.django_db

IMEI_A = "490154203237518"
IMEI_B = "356938035643809"


def test_receiving_units_builds_own_offer(variant, warehouse):
    receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"), imei1=IMEI_A)
    receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1100"), imei1=IMEI_B)

    offer = Offer.objects.get(variant=variant, warehouse=warehouse)
    assert (offer.qty_available, offer.cost_usd, offer.lead_time_days) == (2, Decimal("1050.00"), 0)


def test_sold_units_leave_the_offer(variant, warehouse):
    unit = receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"), imei1=IMEI_A)
    unit.status = InventoryUnit.State.SOLD
    unit.save()

    offer = sync_own_offer(variant, warehouse)

    assert offer.qty_available == 0


def test_invalid_imei_rejected(variant, warehouse):
    with pytest.raises(ValidationError) as exc:
        receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"), imei1="490154203237519")

    assert "imei1" in exc.value.message_dict
    assert not Offer.objects.exists()


def test_imei_is_unique(variant, warehouse):
    receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"), imei1=IMEI_A)

    with pytest.raises(ValidationError):
        receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"), imei1=IMEI_A)


def test_imei_or_serial_required(variant, warehouse):
    with pytest.raises(ValidationError):
        receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"))

    unit = receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("700"), serial="DMPXK1234")
    assert unit.imei1 == ""


def test_second_imei_must_differ(variant, warehouse):
    with pytest.raises(ValidationError) as exc:
        receive_unit(variant=variant, warehouse=warehouse, cost_usd=Decimal("1000"), imei1=IMEI_A, imei2=IMEI_A)

    assert "imei2" in exc.value.message_dict


def test_only_serialized_categories(apple, warehouse, make_variant):
    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    case = ProductModel.objects.create(category=cases, brand=apple, slug="case", name_ru="Чехол",
                                       name_uz="G'ilof", is_accessory=True)
    case_variant = make_variant(case, "CASE-1", {})
    case_variant.save()

    with pytest.raises(ValidationError) as exc:
        receive_unit(variant=case_variant, warehouse=warehouse, cost_usd=Decimal("5"), serial="X1")

    assert "variant" in exc.value.message_dict
