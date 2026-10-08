"""Нормализация текста для поиска: регистр, транслитерация, синонимы. Без БД.

Одна и та же нормализация применяется к индексу товаров и к запросу покупателя.
"""

import re
from collections.abc import Mapping

CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}
APOSTROPHES = {ord(char): None for char in "'ʻʼ‘’`"}


def transliterate(text: str) -> str:
    return "".join(CYRILLIC_TO_LATIN.get(char, char) for char in text)


def normalize(text: str) -> str:
    text = transliterate(text.lower().translate(APOSTROPHES))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", text)
    return " ".join(text.split())


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def expand_synonyms(words: list[str], synonyms: Mapping[str, str], max_words: int = 3) -> list[str]:
    """Заменить синонимы, сначала самые длинные фразы."""
    result: list[str] = []
    index = 0
    while index < len(words):
        for size in range(min(max_words, len(words) - index), 0, -1):
            phrase = " ".join(words[index : index + size])
            if phrase in synonyms:
                result.extend(synonyms[phrase].split())
                index += size
                break
        else:
            result.append(words[index])
            index += 1
    return result
