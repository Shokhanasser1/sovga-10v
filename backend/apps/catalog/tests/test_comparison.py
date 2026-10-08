import pytest

from apps.catalog.comparison import CompareSpec, best_indexes, build_comparison, compare_variants
from apps.catalog.models import Brand, Category, ProductModel


def test_higher_battery_wins():
    assert best_indexes([5000, 4000, 4500], "higher_better") == [0]


def test_lower_weight_wins():
    assert best_indexes([199, 170, 210], "lower_better") == [1]


def test_ties_highlight_all_winners():
    assert best_indexes([256, 512, 512], "higher_better") == [1, 2]


def test_all_equal_highlights_nothing():
    assert best_indexes([128, 128], "higher_better") == []


def test_missing_values_are_ignored():
    assert best_indexes([None, 4000, 5000], "higher_better") == [2]


def test_single_number_is_not_highlighted():
    assert best_indexes([None, 5], "higher_better") == []


def test_no_direction_no_highlight():
    assert best_indexes([1, 2], "none") == []


def test_build_comparison_skips_attributes_nobody_has():
    specs = [
        CompareSpec("battery_mah", "Батарея", "мА·ч", "higher_better"),
        CompareSpec("stylus", "Стилус", "", "none"),
    ]

    rows = build_comparison(specs, [{"battery_mah": 5000}, {"battery_mah": 4000}])

    assert [row.code for row in rows] == ["battery_mah"]
    assert rows[0].values == (5000, 4000)
    assert rows[0].best == (0,)


@pytest.mark.django_db
def test_compare_variants_merges_model_axes_and_variant_attributes(iphone, phones, make_variant):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    galaxy = ProductModel.objects.create(
        category=phones, brand=samsung, slug="galaxy-s26", name_ru="Galaxy S26",
        name_uz="Galaxy S26", attributes={"battery_mah": 5000},
    )
    a = make_variant(iphone, "IP-256", {"storage_gb": 256, "color": "black"}, attributes={"weight_g": 199})
    b = make_variant(galaxy, "S-512", {"storage_gb": 512, "color": "white"}, attributes={"weight_g": 220})
    a.save()
    b.save()

    rows = {row.code: row for row in compare_variants([a, b])}

    assert rows["battery_mah"].best == (1,)
    assert rows["storage_gb"].best == (1,)
    assert rows["weight_g"].best == (0,)
    assert rows["color"].best == ()
    assert rows["color"].values == ("black", "white")


@pytest.mark.django_db
def test_compare_variants_rejects_mixed_categories(iphone, apple, make_variant):
    cases = Category.objects.create(slug="cases", name_ru="Чехлы", name_uz="G'iloflar")
    case = ProductModel.objects.create(
        category=cases, brand=apple, slug="case", name_ru="Чехол", name_uz="G'ilof", is_accessory=True,
    )
    a = make_variant(iphone, "IP-256", {"storage_gb": 256, "color": "black"})
    b = make_variant(case, "CASE-1", {})
    a.save()
    b.save()

    with pytest.raises(ValueError):
        compare_variants([a, b])
