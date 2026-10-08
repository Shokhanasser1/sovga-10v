"""Проверка значений атрибутов по их определениям. Чистые функции, без БД."""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class AttrSpec:
    code: str
    type: str  # number | enum | bool | text
    enum_values: tuple[str, ...] = ()
    is_required: bool = False


def _type_error(spec: AttrSpec, value: object) -> str | None:
    if spec.type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "ожидается число"
    elif spec.type == "bool":
        if not isinstance(value, bool):
            return "ожидается true/false"
    elif spec.type == "text":
        if not isinstance(value, str):
            return "ожидается строка"
    elif spec.type == "enum":
        if value not in spec.enum_values:
            return f"допустимо: {', '.join(spec.enum_values)}"
    return None


def validate_values(specs: Iterable[AttrSpec], values: object) -> list[str]:
    """Вернуть список ошибок; пустой список — значения корректны."""
    if not isinstance(values, Mapping):
        return ["ожидается объект {код: значение}"]
    by_code = {spec.code: spec for spec in specs}
    errors = [f"{code}: неизвестный атрибут" for code in sorted(values.keys() - by_code.keys())]
    for code, spec in sorted(by_code.items()):
        value = values.get(code)
        if value is None:
            if spec.is_required:
                errors.append(f"{code}: обязательный атрибут")
            continue
        problem = _type_error(spec, value)
        if problem:
            errors.append(f"{code}: {problem}")
    return errors


def canonical_key(values: Mapping) -> str:
    """Стабильная строка для сравнения наборов значений независимо от порядка ключей."""
    return json.dumps(values, sort_keys=True, ensure_ascii=False)
