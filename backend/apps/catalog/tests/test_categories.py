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
