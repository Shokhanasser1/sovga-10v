"""Загрузка прайсов: по ссылке (Google Sheets CSV, JSON API) и из файла."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import requests

from .feeds import parse_rows, read_csv, read_json, read_xlsx, validate_columns
from .importer import import_feed
from .models import Supplier, SupplierFeedRun

URL_CONNECTORS = (Supplier.Connector.API, Supplier.Connector.SHEET)


def fetch_feed_records(
    supplier: Supplier, http_get: Callable[..., requests.Response] = requests.get
) -> list[dict]:
    response = http_get(supplier.feed_url, timeout=30)
    response.raise_for_status()
    if supplier.connector_type == Supplier.Connector.API:
        return read_json(response.json())
    return read_csv(response.content.decode("utf-8-sig"))


def sync_supplier(
    supplier: Supplier, now: datetime, http_get: Callable[..., requests.Response] = requests.get
) -> SupplierFeedRun:
    """Ошибка загрузки не трогает остатки: они сами устареют по TTL."""
    problems = validate_columns(supplier.columns)
    if not supplier.feed_url:
        problems.append("не задана ссылка на прайс")
    if problems:
        return SupplierFeedRun.objects.create(
            supplier=supplier, started_at=now, error="; ".join(problems)
        )
    try:
        records = fetch_feed_records(supplier, http_get)
    except (requests.RequestException, ValueError) as error:
        return SupplierFeedRun.objects.create(
            supplier=supplier, started_at=now, error=f"Ошибка загрузки: {error}"
        )
    return import_feed(supplier, parse_rows(records, supplier.columns), now)


def read_file(path: str | Path) -> list[dict]:
    """.xlsx или .csv (UTF-8 или Windows-1251 — как сохраняет русский Excel)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if suffix == ".csv":
        data = path.read_bytes()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1251")
        return read_csv(text)
    raise ValueError("Поддерживаются файлы .xlsx и .csv")
