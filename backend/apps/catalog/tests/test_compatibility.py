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
