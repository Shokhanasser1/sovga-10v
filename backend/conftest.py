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
