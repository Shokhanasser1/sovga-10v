from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalog.models import Brand, Category
from apps.promo.models import GiftPolicy
from apps.promo.selection import select_gift_policy

pytestmark = pytest.mark.django_db


@pytest.fixture
def variant(iphone, make_variant):
    variant = make_variant(iphone, "IP16P-256", {"storage_gb": 256, "color": "black"})
    variant.save()
    return variant


def policy(name, **kwargs):
    kwargs.setdefault("budget_pct_of_net_margin", Decimal("10"))
    kwargs.setdefault("budget_cap_uzs", 150_000)
    return GiftPolicy.objects.create(name=name, **kwargs)


def test_highest_priority_wins(variant, phones):
    policy("общая")
    best = policy("смартфоны", category=phones, priority=10)

    assert select_gift_policy(variant, 14_000_000) == best


def test_parent_category_policy_applies_to_child(variant, phones):
    electronics = Category.objects.create(slug="electronics", name_ru="Электроника", name_uz="Elektronika")
    phones.parent = electronics
    phones.save()
    parent_policy = policy("электроника", category=electronics)

    assert select_gift_policy(variant, 14_000_000) == parent_policy


def test_other_brand_policy_is_skipped(variant):
    samsung = Brand.objects.create(slug="samsung", name="Samsung")
    policy("samsung", brand=samsung, priority=10)
    fallback = policy("общая")

    assert select_gift_policy(variant, 14_000_000) == fallback


def test_price_range_is_respected(variant):
    policy("дорогие", min_price_uzs=20_000_000, priority=10)
    regular = policy("до 20 млн", max_price_uzs=20_000_000)

    assert select_gift_policy(variant, 14_000_000) == regular


def test_expired_and_future_policies_are_skipped(variant):
    now = timezone.now()
    policy("прошлая", active_to=now - timedelta(days=1), priority=10)
    policy("будущая", active_from=now + timedelta(days=1), priority=10)
    current = policy("текущая", active_from=now - timedelta(days=1), active_to=now + timedelta(days=1))

    assert select_gift_policy(variant, 14_000_000, at=now) == current


def test_inactive_policy_and_no_match_give_none(variant):
    policy("выключена", is_active=False)

    assert select_gift_policy(variant, 14_000_000) is None


def test_policy_rejects_inverted_ranges():
    invalid = GiftPolicy(
        name="x", budget_pct_of_net_margin=Decimal("10"), budget_cap_uzs=1,
        min_price_uzs=10, max_price_uzs=5,
    )

    with pytest.raises(ValidationError) as exc:
        invalid.full_clean()

    assert "max_price_uzs" in exc.value.message_dict
