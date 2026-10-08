"""Загрузка прайсов: по ссылке (Google Sheets CSV, JSON API) и из файла."""

import io
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


FILE_SUFFIXES = (".xlsx", ".xlsm", ".csv")


def read_bytes(filename: str, data: bytes) -> list[dict]:
    """.xlsx или .csv (UTF-8 или Windows-1251 — как сохраняет русский Excel)."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        return read_xlsx(io.BytesIO(data))
    if suffix == ".csv":
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1251")
        return read_csv(text)
    raise ValueError("Поддерживаются файлы .xlsx и .csv")


def read_file(path: str | Path) -> list[dict]:
    path = Path(path)
    return read_bytes(path.name, path.read_bytes())


def import_file(supplier: Supplier, filename: str, data: bytes, now: datetime) -> SupplierFeedRun:
    """Прайс файлом (например, присланный в бот). Ошибка — запись в журнале, остатки не трогаем."""
    problems = validate_columns(supplier.columns)
    if problems:
        return SupplierFeedRun.objects.create(supplier=supplier, started_at=now, error="; ".join(problems))
    try:
        records = read_bytes(filename, data)
    except Exception:  # чужой файл может быть каким угодно — не падаем, а сообщаем
        return SupplierFeedRun.objects.create(
            supplier=supplier, started_at=now, error="Файл не читается — сохраните прайс заново как .xlsx или .csv"
        )
    return import_feed(supplier, parse_rows(records, supplier.columns), now)
