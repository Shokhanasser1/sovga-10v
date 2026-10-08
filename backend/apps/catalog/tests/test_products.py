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
