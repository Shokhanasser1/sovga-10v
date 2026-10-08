import pytest

from apps.catalog.labels import variant_title

pytestmark = pytest.mark.django_db


def test_title_uses_human_values(variant, phones):
    phones.attribute_definitions.filter(code="storage_gb").update(unit="ГБ")

    assert variant_title(variant) == "iPhone 16 Pro · 256 ГБ · Чёрный"


def test_unknown_values_stay_as_is(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-X", {"storage_gb": 1024, "color": "desert"})

    assert variant_title(variant) == "iPhone 16 Pro · 1024 · desert"
