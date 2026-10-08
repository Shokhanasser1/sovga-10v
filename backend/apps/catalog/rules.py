"""Правила совместимости аксессуаров по характеристикам. Чистые функции, без БД."""

from collections.abc import Mapping

OPERATORS = {
    "eq": lambda device, target: device == target,
    "lte": lambda device, target: device <= target,
    "gte": lambda device, target: device >= target,
    "in": lambda device, target: device in target,
}


def validate_rule(conditions: object) -> list[str]:
    if not isinstance(conditions, list) or not conditions:
        return ["правило — непустой список условий"]
    errors = []
    for index, condition in enumerate(conditions, start=1):
        prefix = f"условие {index}"
        if not isinstance(condition, Mapping):
            errors.append(f"{prefix}: ожидается объект")
            continue
        if not isinstance(condition.get("attr"), str):
            errors.append(f"{prefix}: нужен attr")
        if condition.get("op") not in OPERATORS:
            errors.append(f"{prefix}: op — одно из {', '.join(OPERATORS)}")
        if ("value" in condition) == ("accessory_attr" in condition):
            errors.append(f"{prefix}: нужно ровно одно из value / accessory_attr")
    return errors


def rule_matches(
    conditions: list[Mapping], device_attrs: Mapping, accessory_attrs: Mapping
) -> bool:
    """Все условия выполняются: device[attr] OP (value | accessory[accessory_attr])."""
    for condition in conditions:
        device_value = device_attrs.get(condition["attr"])
        if "value" in condition:
            target = condition["value"]
        else:
            target = accessory_attrs.get(condition["accessory_attr"])
        if device_value is None or target is None:
            return False
        try:
            if not OPERATORS[condition["op"]](device_value, target):
                return False
        except TypeError:
            return False
    return True
