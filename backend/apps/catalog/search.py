"""Поиск по каталогу в базе данных: точное совпадение по началу слов + нечёткий запасной."""

from .models import SearchSynonym


def load_synonyms() -> dict[str, str]:
    return dict(SearchSynonym.objects.values_list("term", "replacement"))
