import json
from decimal import Decimal

import pytest
from openpyxl import Workbook

from apps.sourcing.feeds import parse_rows, read_csv, read_json, read_xlsx, validate_columns

COLUMNS = {"code": "Артикул", "name": "Наименование", "price": "Цена", "qty": "Остаток"}


def record(code="A1", name="iPhone 16 Pro 256GB Black", price="999.00", qty="5"):
    return {"Артикул": code, "Наименование": name, "Цена": price, "Остаток": qty}


def test_parse_valid_row():
    [row] = parse_rows([record()], COLUMNS)

    assert (row.code, row.name, row.price_usd, row.qty, row.error) == (
        "A1", "iPhone 16 Pro 256GB Black", Decimal("999.00"), 5, ""
    )
    assert row.raw["Артикул"] == "A1"


@pytest.mark.parametrize(
    "price, expected",
    [("1299", Decimal("1299.00")), ("1 299,50", Decimal("1299.50")),
     ("$1,299.00", Decimal("1299.00")), (1299.5, Decimal("1299.50")), ("договорная", None)],
)
def test_price_formats(price, expected):
    [row] = parse_rows([record(price=price)], COLUMNS)

    assert row.price_usd == expected


@pytest.mark.parametrize(
    "qty, expected",
    [("5", 5), (5.0, 5), (7, 7), ("10+", 10), (">10", 10), ("нет", None), ("", None)],
)
def test_qty_formats(qty, expected):
    [row] = parse_rows([record(qty=qty)], COLUMNS)

    assert row.qty == expected


@pytest.mark.parametrize(
    "overrides, error",
    [({"code": ""}, "нет кода"), ({"price": "0"}, "некорректная цена"),
     ({"price": "abc"}, "некорректная цена"), ({"qty": "нет"}, "некорректный остаток")],
)
def test_row_errors(overrides, error):
    [row] = parse_rows([record(**overrides)], COLUMNS)

    assert row.error == error


def test_empty_lines_are_skipped():
    rows = parse_rows([record(), {"Артикул": "", "Наименование": None, "Цена": "", "Остаток": ""}], COLUMNS)

    assert len(rows) == 1


def test_name_column_is_optional():
    columns = {"code": "Артикул", "price": "Цена", "qty": "Остаток"}

    [row] = parse_rows([record()], columns)

    assert row.name == ""
    assert row.error == ""


def test_validate_columns():
    assert validate_columns(COLUMNS) == []
    assert validate_columns({"code": "Артикул"}) == [
        "не задана колонка: price", "не задана колонка: qty"
    ]


def test_read_csv_with_semicolons_and_bom():
    text = "﻿Артикул;Цена;Остаток\nA1;999,00;5\nA2;1 100,00;0\n"

    assert read_csv(text) == [
        {"Артикул": "A1", "Цена": "999,00", "Остаток": "5"},
        {"Артикул": "A2", "Цена": "1 100,00", "Остаток": "0"},
    ]


def test_read_csv_with_commas():
    assert read_csv('Артикул,Цена,Остаток\nA1,"999.00",5\n') == [
        {"Артикул": "A1", "Цена": "999.00", "Остаток": "5"}
    ]


def test_read_xlsx_skips_title_rows(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([None, None, None])
    sheet.append(["Артикул", "Цена", "Остаток"])
    sheet.append(["A1", 999.5, 5])
    sheet.append([None, None, None])
    path = tmp_path / "price.xlsx"
    workbook.save(path)

    assert read_xlsx(path) == [{"Артикул": "A1", "Цена": 999.5, "Остаток": 5}]


def test_read_json_accepts_list_and_wrapped_items():
    items = [{"sku": "A1", "price": 999, "stock": 5}]

    assert read_json(items) == items
    assert read_json({"items": items}) == items
    assert read_json(json.loads('{"data": [{"sku": "A1"}]}')) == [{"sku": "A1"}]


def test_read_json_rejects_unknown_shape():
    with pytest.raises(ValueError):
        read_json({"result": "ok"})
