from django.core.management.base import BaseCommand

from apps.catalog.search import rebuild_search_index


class Command(BaseCommand):
    help = "Пересобрать поисковый текст товаров (после переименования брендов и категорий)"

    def handle(self, *args, **options) -> None:
        self.stdout.write(f"Обновлено товаров: {rebuild_search_index()}")
