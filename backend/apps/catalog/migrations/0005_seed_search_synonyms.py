from django.db import migrations

from apps.catalog.search_text import normalize

STARTER_SYNONYMS = [
    ("айфон", "iphone"), ("айпон", "iphone"), ("aypon", "iphone"), ("aifon", "iphone"),
    ("ифон", "iphone"), ("айпад", "ipad"), ("эйрподс", "airpods"), ("макбук", "macbook"),
    ("samsun", "samsung"), ("галакси", "galaxy"), ("гэлакси", "galaxy"), ("сяоми", "xiaomi"),
    ("ксиаоми", "xiaomi"), ("шаоми", "xiaomi"), ("xiomi", "xiaomi"), ("хуавей", "huawei"),
    ("хуавэй", "huawei"), ("поко", "poco"), ("пиксель", "pixel"), ("про макс", "pro max"),
    ("макс", "max"), ("чехол", "чехлы"), ("зарядка", "зарядные"), ("зарядник", "зарядные"),
    ("стекло", "защитные стекла"),
]


def seed(apps, schema_editor):
    SearchSynonym = apps.get_model("catalog", "SearchSynonym")
    seen = set()
    for term, replacement in STARTER_SYNONYMS:
        term, replacement = normalize(term), normalize(replacement)
        if term == replacement or term in seen:
            continue
        seen.add(term)
        SearchSynonym.objects.get_or_create(term=term, defaults={"replacement": replacement})


def unseed(apps, schema_editor):
    apps.get_model("catalog", "SearchSynonym").objects.filter(
        term__in=[normalize(term) for term, _ in STARTER_SYNONYMS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_searchsynonym")]

    operations = [migrations.RunPython(seed, unseed)]
