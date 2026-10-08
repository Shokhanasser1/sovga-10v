"""Фильтры, сортировка и фасеты листинга."""

from collections import Counter
from collections.abc import Mapping

from django.db.models import Case, F, IntegerField, QuerySet, When

from .models import AttributeDefinition, Category, ProductModel, Status, Variant
from .search import search_products

FACET_PREFIX = "f."
SORT_ORDER = {
    "price_asc": (F("price_from_uzs").asc(nulls_last=True), "name_ru"),
    "price_desc": (F("price_from_uzs").desc(nulls_last=True), "name_ru"),
    "name": ("name_ru",),
}


def facet_definitions(category: Category | None) -> dict[str, AttributeDefinition]:
    if category is None:
        return {}
    return {
        d.code: d for d in category.effective_attributes() if d.is_facet and "__" not in d.code
    }


def coerce(definition: AttributeDefinition, raw: str):
    """Значение из URL → тип атрибута; None, если не приводится."""
    if definition.type == AttributeDefinition.Type.NUMBER:
        try:
            number = float(raw)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    if definition.type == AttributeDefinition.Type.BOOL:
        return {"true": True, "1": True, "false": False, "0": False}.get(raw.lower())
    return raw


def _int_param(params: Mapping[str, str], name: str) -> int | None:
    try:
        return int(params.get(name, ""))
    except ValueError:
        return None


def apply_filters(
    queryset: QuerySet[ProductModel], params: Mapping[str, str], category: Category | None
) -> QuerySet[ProductModel]:
    brands = [slug for slug in params.get("brand", "").split(",") if slug]
    if brands:
        queryset = queryset.filter(brand__slug__in=brands)
    definitions = facet_definitions(category)
    for key, raw in params.items():
        if not key.startswith(FACET_PREFIX):
            continue
        definition = definitions.get(key.removeprefix(FACET_PREFIX))
        if definition is None:
            continue
        values = [coerce(definition, part) for part in raw.split(",")]
        values = [value for value in values if value is not None]
        if not values:
            continue
        if definition.level == AttributeDefinition.Level.MODEL:
            queryset = queryset.filter(**{f"attributes__{definition.code}__in": values})
        else:
            field = "axes" if definition.is_variant_axis else "attributes"
            matching = Variant.objects.filter(
                status=Status.ACTIVE, **{f"{field}__{definition.code}__in": values}
            ).values("product_model_id")
            queryset = queryset.filter(pk__in=matching)
    price_min = _int_param(params, "price_min")
    if price_min is not None:
        queryset = queryset.filter(price_from_uzs__gte=price_min)
    price_max = _int_param(params, "price_max")
    if price_max is not None:
        queryset = queryset.filter(price_from_uzs__lte=price_max)
    if params.get("available") in ("1", "true"):
        queryset = queryset.filter(is_available=True)
    return queryset


def search_and_sort(
    queryset: QuerySet[ProductModel], query: str, sort: str | None
) -> QuerySet[ProductModel]:
    """Доступные товары всегда выше; с запросом по умолчанию — по релевантности."""
    query = query.strip()
    sort = sort or ("relevance" if query else "name")
    if query:
        ids = [product.pk for product in search_products(query, queryset)]
        if not ids:
            return queryset.none()
        queryset = queryset.filter(pk__in=ids)
        if sort == "relevance":
            relevance = Case(
                *[When(pk=pk, then=position) for position, pk in enumerate(ids)],
                output_field=IntegerField(),
            )
            return queryset.order_by("-is_available", relevance)
    return queryset.order_by("-is_available", *SORT_ORDER.get(sort, SORT_ORDER["name"]))


def _value_order(item: tuple) -> tuple:
    value = item[0]
    return (1, 0, value) if isinstance(value, str) else (0, value, "")


def _values_of(definition: AttributeDefinition, product: ProductModel) -> set:
    if definition.level == AttributeDefinition.Level.MODEL:
        return {product.attributes.get(definition.code)} - {None}
    field = "axes" if definition.is_variant_axis else "attributes"
    found = {
        getattr(variant, field).get(definition.code)
        for variant in product.variants.all()
        if variant.status == Status.ACTIVE
    }
    return found - {None}


def compute_facets(queryset: QuerySet[ProductModel], category: Category | None) -> dict:
    products = list(queryset.select_related("brand").prefetch_related("variants"))
    brand_counts = Counter((p.brand.slug, p.brand.name) for p in products)
    attributes = []
    definitions = sorted(facet_definitions(category).values(), key=lambda d: (d.sort_order, d.code))
    for definition in definitions:
        counter: Counter = Counter()
        for product in products:
            counter.update(_values_of(definition, product))
        if counter:
            attributes.append(
                {
                    "code": definition.code,
                    "name_ru": definition.name_ru,
                    "name_uz": definition.name_uz,
                    "unit": definition.unit,
                    "type": definition.type,
                    "values": [
                        {"value": value, "count": count}
                        for value, count in sorted(counter.items(), key=_value_order)
                    ],
                }
            )
    prices = [p.price_from_uzs for p in products if p.price_from_uzs is not None]
    brands = sorted(brand_counts.items(), key=lambda item: item[0][1])
    return {
        "brands": [{"slug": slug, "name": name, "count": count} for (slug, name), count in brands],
        "attributes": attributes,
        "price": {"min": min(prices, default=None), "max": max(prices, default=None)},
    }
