from apps.catalog.attributes import AttrSpec, canonical_key, validate_values

SPECS = [
    AttrSpec("battery_mah", "number", is_required=True),
    AttrSpec("color", "enum", enum_values=("black", "white")),
    AttrSpec("nfc", "bool"),
    AttrSpec("chipset", "text"),
]


def test_valid_values_have_no_errors():
    values = {"battery_mah": 5000, "color": "black", "nfc": True, "chipset": "A18"}

    assert validate_values(SPECS, values) == []


def test_unknown_attribute_is_reported():
    assert validate_values(SPECS, {"battery_mah": 1, "ram": 8}) == ["ram: неизвестный атрибут"]


def test_missing_required_attribute_is_reported():
    assert validate_values(SPECS, {}) == ["battery_mah: обязательный атрибут"]


def test_none_counts_as_missing():
    assert validate_values(SPECS, {"battery_mah": None}) == ["battery_mah: обязательный атрибут"]


def test_bool_is_not_accepted_as_number():
    assert validate_values(SPECS, {"battery_mah": True}) == ["battery_mah: ожидается число"]


def test_enum_value_outside_list_is_reported():
    errors = validate_values(SPECS, {"battery_mah": 1, "color": "red"})

    assert errors == ["color: допустимо: black, white"]


def test_wrong_types_for_bool_and_text():
    errors = validate_values(SPECS, {"battery_mah": 1, "nfc": "yes", "chipset": 18})

    assert errors == ["chipset: ожидается строка", "nfc: ожидается true/false"]


def test_non_object_is_rejected():
    assert validate_values(SPECS, ["battery_mah"]) == ["ожидается объект {код: значение}"]


def test_canonical_key_ignores_key_order():
    assert canonical_key({"storage_gb": 256, "color": "black"}) == canonical_key(
        {"color": "black", "storage_gb": 256}
    )
    assert canonical_key({"b": 1, "a": "x"}) == '{"a": "x", "b": 1}'
