"""Поиск по каталогу в базе данных: совпадение по началу слов, запасной нечёткий поиск."""

from difflib import SequenceMatcher

from django.db.models import Q, QuerySet

from .models import Category, ProductModel, SearchSynonym, Status
from .search_text import expand_synonyms, normalize, tokens

FUZZY_THRESHOLD = 0.75
MAX_QUERY_LENGTH = 100


def load_synonyms() -> dict[str, str]:
    return dict(SearchSynonym.objects.values_list("term", "replacement"))


def query_words(query: str) -> list[str]:
    return expand_synonyms(tokens(query[:MAX_QUERY_LENGTH]), load_synonyms())


def _rank(product: ProductModel, words: list[str]) -> tuple:
    name = normalize(product.name_ru)
    return (not name.startswith(words[0]), len(name), name)


def _fuzzy_score(words: list[str], product: ProductModel) -> float | None:
    """Каждое слово запроса должно быть похоже хотя бы на одно слово товара."""
    candidates = product.search_text.split()
    scores = []
    for word in words:
        best = max(
            (
                1.0 if candidate.startswith(word) else SequenceMatcher(None, word, candidate).ratio()
                for candidate in candidates
            ),
            default=0.0,
        )
        if best < FUZZY_THRESHOLD:
            return None
        scores.append(best)
    return sum(scores) / len(scores)


def search_products(
    query: str, queryset: QuerySet[ProductModel] | None = None
) -> list[ProductModel]:
    base = queryset if queryset is not None else ProductModel.objects.filter(status=Status.ACTIVE)
    base = base.select_related("brand", "category")
    words = query_words(query)
    if not words:
        return []
    condition = Q()
    for word in words:
        condition &= Q(search_text__contains=f" {word}")
    exact = list(base.filter(condition))
    if exact:
        return sorted(exact, key=lambda product: _rank(product, words))
    scored = []
    for product in base:
        score = _fuzzy_score(words, product)
        if score is not None:
            scored.append((score, product))
    scored.sort(key=lambda item: (-item[0], item[1].name_ru))
    return [product for _, product in scored]


def suggest(query: str, max_products: int = 8, max_categories: int = 3) -> dict[str, list]:
    words = query_words(query)
    if not words:
        return {"products": [], "categories": []}
    categories = []
    for category in Category.objects.order_by("name_ru"):
        text = f" {normalize(f'{category.name_ru} {category.name_uz}')} "
        if all(f" {word}" in text for word in words):
            categories.append(category)
    return {
        "products": search_products(query)[:max_products],
        "categories": categories[:max_categories],
    }


def rebuild_search_index() -> int:
    products = list(ProductModel.objects.select_related("brand", "category"))
    for product in products:
        product.search_text = product.build_search_text()
    ProductModel.objects.bulk_update(products, ["search_text"], batch_size=500)
    return len(products)
