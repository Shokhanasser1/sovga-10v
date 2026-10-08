from apps.catalog.rules import rule_matches, validate_rule

CHARGER_RULE = [
    {"attr": "charge_port", "op": "eq", "value": "usb-c"},
    {"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"},
]


def test_charger_matches_when_port_and_power_fit():
    assert rule_matches(CHARGER_RULE, {"charge_port": "usb-c", "max_charge_w": 27}, {"output_w": 30})


def test_charger_rejected_when_too_weak_for_device():
    assert not rule_matches(CHARGER_RULE, {"charge_port": "usb-c", "max_charge_w": 45}, {"output_w": 30})


def test_missing_device_attribute_never_matches():
    assert not rule_matches(CHARGER_RULE, {"charge_port": "usb-c"}, {"output_w": 30})


def test_in_operator():
    rule = [{"attr": "charge_port", "op": "in", "value": ["usb-c", "lightning"]}]

    assert rule_matches(rule, {"charge_port": "lightning"}, {})


def test_incomparable_types_do_not_raise():
    rule = [{"attr": "max_charge_w", "op": "lte", "value": 30}]

    assert not rule_matches(rule, {"max_charge_w": "fast"}, {})


def test_validate_rule_reports_structural_errors():
    errors = validate_rule([{"attr": "x", "op": "like", "value": 1, "accessory_attr": "y"}])

    assert errors == [
        "условие 1: op — одно из eq, lte, gte, in",
        "условие 1: нужно ровно одно из value / accessory_attr",
    ]


def test_empty_rule_is_invalid():
    assert validate_rule([]) == ["правило — непустой список условий"]


def test_valid_rule_has_no_errors():
    assert validate_rule(CHARGER_RULE) == []
