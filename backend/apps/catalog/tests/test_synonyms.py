import pytest

from apps.catalog.models import SearchSynonym
from apps.catalog.search import load_synonyms

pytestmark = pytest.mark.django_db


def test_synonym_is_stored_normalized():
    SearchSynonym.objects.create(term="Реалми", replacement="Realme")

    assert load_synonyms()["realmi"] == "realme"


def test_starter_synonyms_are_seeded():
    synonyms = load_synonyms()

    assert synonyms["ayfon"] == "iphone"
    assert synonyms["aypon"] == "iphone"
    assert synonyms["galaksi"] == "galaxy"
    assert synonyms["chehol"] == "chehli"
