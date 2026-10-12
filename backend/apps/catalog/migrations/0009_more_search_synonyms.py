from django.db import migrations

from apps.catalog.search_text import normalize

MORE_SYNONYMS = [
    ("эпл", "apple"), ("эппл", "apple"), ("вотч", "watch"), ("ватч", "watch"), ("эйр", "air"),
    ("сони", "sony"), ("бадс", "buds"), ("павербанк", "powerbank"), ("повербанк", "powerbank"),
    ("пауэрбанк", "powerbank"), ("power bank", "powerbank"),
]


def seed(apps, schema_editor):
    SearchSynonym = apps.get_model("catalog", "SearchSynonym")
    for term, replacement in MORE_SYNONYMS:
        SearchSynonym.objects.get_or_create(term=normalize(term), defaults={"replacement": normalize(replacement)})


def unseed(apps, schema_editor):
    apps.get_model("catalog", "SearchSynonym").objects.filter(
        term__in=[normalize(term) for term, _ in MORE_SYNONYMS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("catalog", "0008_category_warranty_months")]

    operations = [migrations.RunPython(seed, unseed)]
