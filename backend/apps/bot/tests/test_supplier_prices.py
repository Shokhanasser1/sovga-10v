import pytest
import requests

from apps.bot.dispatch import handle_update
from apps.notifications.telegram import TelegramError, download_file
from apps.sourcing.models import Offer, SupplierFeedRun, SupplierSkuMap

from .conftest import NOW

pytestmark = pytest.mark.django_db
CHAT = 777
PRICE_CSV = "Артикул;Наименование;Цена;Остаток\nAPL-16P-256;iPhone 16 Pro 256 Black;1010;4\nX-9;Неизвестная штука;5;1\n"


@pytest.fixture
def supplier(make_supplier, variant):
    supplier = make_supplier("Опт Чиланзар", connector_type="telegram", telegram_chat_id=CHAT)
    SupplierSkuMap.objects.create(supplier=supplier, supplier_code="APL-16P-256", variant=variant)
    return supplier


@pytest.fixture
def files(monkeypatch):
    """Файлы, которые «лежат» в Telegram: file_id → содержимое."""
    stored: dict[str, bytes] = {}

    def fake_download(file_id, max_bytes, **kwargs):
        return stored[file_id]

    monkeypatch.setattr("apps.notifications.telegram.download_file", fake_download)
    return stored


def send_document(chat_id: int, name: str, size: int = 100, file_id: str = "f1") -> None:
    document = {"file_id": file_id, "file_name": name, "file_size": size}
    handle_update({"update_id": 1, "message": {"chat": {"id": chat_id}, "document": document}}, NOW)


def test_supplier_price_list_is_imported(bot, telegram, files, supplier, variant):
    files["f1"] = PRICE_CSV.encode("cp1251")  # русский Excel сохраняет CSV в Windows-1251

    send_document(CHAT, "прайс.csv")

    offer = Offer.objects.get(supplier=supplier, variant=variant)
    assert (offer.qty_available, offer.cost_usd) == (4, 1010)
    reply = telegram.sent(CHAT)[-1]
    assert "Прайс принят" in reply and "строк 2" in reply and "сопоставлено 1" in reply and "ждут сопоставления 1" in reply


def test_strangers_files_are_ignored(bot, telegram, files, supplier):
    send_document(999, "прайс.csv")

    assert not SupplierFeedRun.objects.exists()
    assert "/orders" in telegram.sent(999)[-1]


@pytest.mark.parametrize("name, size, expected", [
    ("прайс.pdf", 100, ".xlsx или .csv"),
    ("прайс.xlsx", 6 * 1024 * 1024, "5 МБ"),
])
def test_wrong_files(bot, telegram, files, supplier, name, size, expected):
    send_document(CHAT, name, size=size)

    assert expected in telegram.sent(CHAT)[-1]
    assert not SupplierFeedRun.objects.exists()


def test_broken_file_is_reported(bot, telegram, files, supplier):
    files["f1"] = b"not a zip"

    send_document(CHAT, "прайс.xlsx")

    assert "не принят" in telegram.sent(CHAT)[-1]
    assert SupplierFeedRun.objects.get().error


def test_supplier_without_columns(bot, telegram, files, supplier):
    supplier.columns = {}
    supplier.save()
    files["f1"] = PRICE_CSV.encode()

    send_document(CHAT, "прайс.csv")

    assert "не принят" in telegram.sent(CHAT)[-1]


class FakeResponse:
    def __init__(self, content=b"", error=None):
        self.content, self.error = content, error

    def raise_for_status(self):
        if self.error:
            raise self.error


def test_download_file(bot, telegram):
    telegram.files = {}
    got = []

    def http_get(url, **kwargs):
        got.append(url)
        return FakeResponse(b"price")

    assert download_file("f1", 100, http_get=http_get) == b"price"
    assert telegram.calls[-1] == ("getFile", {"file_id": "f1"})
    assert got == ["https://api.telegram.org/file/bot123:test/documents/f1.bin"]

    with pytest.raises(TelegramError, match="больше"):
        download_file("f1", 3, http_get=http_get)


def test_download_error_hides_the_token(bot, telegram):
    def http_get(url, **kwargs):
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}")

    with pytest.raises(TelegramError) as error:
        download_file("f1", 100, http_get=http_get)
    assert "123:test" not in str(error.value)
