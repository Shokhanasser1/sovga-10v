"""Публичный сервис совместимости: явные привязки + правила."""

from django.db.models import QuerySet

from .models import AccessoryCompat, CompatRule, ProductModel, Status
from .rules import rule_matches


def is_compatible(accessory: ProductModel, device: ProductModel) -> bool:
    if AccessoryCompat.objects.filter(accessory=accessory, device=device).exists():
        return True
    return any(
        rule_matches(rule.conditions, device.attributes, accessory.attributes)
        for rule in accessory.compat_rules.all()
    )


def compatible_accessories(device: ProductModel) -> QuerySet[ProductModel]:
    ids = set(
        AccessoryCompat.objects.filter(device=device).values_list("accessory_id", flat=True)
    )
    rules = CompatRule.objects.select_related("accessory").filter(accessory__status=Status.ACTIVE)
    for rule in rules:
        if rule_matches(rule.conditions, device.attributes, rule.accessory.attributes):
            ids.add(rule.accessory_id)
    return ProductModel.objects.filter(
        pk__in=ids, status=Status.ACTIVE, is_accessory=True
    ).order_by("name_ru")
