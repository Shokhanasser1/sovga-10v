import json
from decimal import Decimal

import pytest
import requests
from django.core.management import CommandError, call_command
from django.utils import timezone
from openpyxl import Workbook

from apps.sourcing.fetch import read_file, sync_supplier
from apps.sourcing.models import Offer, Supplier, SupplierSkuMap

pytestmark = pytest.mark.django_db

CSV = "Артикул;Наименование;Цена;Остаток\nIP-256-B;iPhone 16 Pro 256 Black;1010,00;4\n"


class FakeResponse:
    def __init__(self, content=b"", status=200):
        self.content = content
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        return json.loads(self.content)


def fake_get(content=b"", status=200):
    return lambda url, timeout: FakeResponse(content, status)


@pytest.fixture
def sheet_supplier(make_supplier, variant):
    supplier = make_supplier(feed_url="https://docs.google.com/spreadsheets/d/x/export?format=csv")
    SupplierSkuMap.objects.create(supplier=supplier, supplier_code="IP-256-B", variant=variant)
    return supplier


def test_sheet_csv_is_imported(sheet_supplier, variant):
    run = sync_supplier(sheet_supplier, timezone.now(), fake_get(CSV.encode("utf-8")))

    assert run.error == ""
    offer = Offer.objects.get(supplier=sheet_supplier)
    assert (offer.cost_usd, offer.qty_available) == (Decimal("1010.00"), 4)


def test_api_json_is_imported(make_supplier, variant):
    supplier = make_supplier(
        connector_type=Supplier.Connector.API, feed_url="https://supplier.example/api/stock",
        columns={"code": "sku", "price": "price_usd", "qty": "stock"},
    )
    SupplierSkuMap.objects.create(supplier=supplier, supplier_code="A1", variant=variant)
    payload = json.dumps({"items": [{"sku": "A1", "price_usd": 995.5, "stock": 7}]}).encode()

    sync_supplier(supplier, timezone.now(), fake_get(payload))

    assert Offer.objects.get(supplier=supplier).qty_available == 7


def test_network_error_keeps_existing_stock(sheet_supplier):
    sync_supplier(sheet_supplier, timezone.now(), fake_get(CSV.encode("utf-8")))

    run = sync_supplier(sheet_supplier, timezone.now(), fake_get(status=503))

    assert "Ошибка загрузки" in run.error
    assert Offer.objects.get(supplier=sheet_supplier).qty_available == 4


def test_supplier_without_columns_is_not_fetched(make_supplier):
    supplier = make_supplier(columns={}, feed_url="https://supplier.example/x.csv")

    def must_not_be_called(url, timeout):
        raise AssertionError("не должно быть запроса")

    run = sync_supplier(supplier, timezone.now(), must_not_be_called)

    assert "не задана колонка: code" in run.error


def test_read_file_supports_cp1251_csv(tmp_path):
    path = tmp_path / "price.csv"
    path.write_bytes("Артикул;Цена;Остаток\nA1;999;5\n".encode("cp1251"))

    assert read_file(path) == [{"Артикул": "A1", "Цена": "999", "Остаток": "5"}]


def test_import_feed_file_command(sheet_supplier, tmp_path):
    workbook = Workbook()
    workbook.active.append(["Артикул", "Наименование", "Цена", "Остаток"])
    workbook.active.append(["IP-256-B", "iPhone", 1000, 2])
    path = tmp_path / "price.xlsx"
    workbook.save(path)

    call_command("import_feed_file", str(sheet_supplier.pk), str(path))

    assert Offer.objects.get(supplier=sheet_supplier).qty_available == 2


def test_import_feed_file_unknown_supplier(tmp_path):
    with pytest.raises(CommandError):
        call_command("import_feed_file", "999", str(tmp_path / "missing.xlsx"))
