import pytest

from apps.catalog.search_text import expand_synonyms, normalize, tokens


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Смартфоны Samsung", "smartfoni samsung"),
        ("Чёрный", "cherniy"),
        ("Qo'shimcha G‘ilof", "qoshimcha gilof"),
        ("ўзбек қўшиқ ғалаба ҳа", "ozbek qoshiq galaba ha"),
        ("iPhone15 Pro", "iphone 15 pro"),
        ("Galaxy S25 Ultra", "galaxy s 25 ultra"),
        ("  iPhone, 16 — Pro!! ", "iphone 16 pro"),
    ],
)
def test_normalize(text, expected):
    assert normalize(text) == expected


def test_memory_written_any_way_is_the_same():
    assert normalize("256 ГБ") == normalize("256GB") == normalize("256 gb") == "256 gb"


def test_tokens():
    assert tokens("Айфон 16") == ["ayfon", "16"]


def test_expand_single_word_synonym():
    assert expand_synonyms(["ayfon", "16"], {"ayfon": "iphone"}) == ["iphone", "16"]


def test_expand_multi_word_synonyms_longest_first():
    synonyms = {"pro maks": "pro max", "maks": "max", "eyrpods": "airpods"}

    assert expand_synonyms(["iphone", "pro", "maks"], synonyms) == ["iphone", "pro", "max"]
    assert expand_synonyms(["maks"], synonyms) == ["max"]
    assert expand_synonyms(["eyrpods", "pro"], synonyms) == ["airpods", "pro"]
