from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.sourcing.feeds import parse_rows, validate_columns
from apps.sourcing.fetch import read_file
from apps.sourcing.importer import import_feed
from apps.sourcing.models import Supplier


class Command(BaseCommand):
    help = "Загрузить прайс поставщика из файла .xlsx или .csv"

    def add_arguments(self, parser) -> None:
        parser.add_argument("supplier_id", type=int)
        parser.add_argument("path")

    def handle(self, *args, supplier_id: int, path: str, **options) -> None:
        try:
            supplier = Supplier.objects.get(pk=supplier_id)
        except Supplier.DoesNotExist as error:
            raise CommandError(f"Нет поставщика с id={supplier_id}") from error
        problems = validate_columns(supplier.columns)
        if problems:
            raise CommandError("; ".join(problems))
        try:
            records = read_file(path)
        except Exception as error:  # битый или чужой файл — понятное сообщение вместо трейсбека
            raise CommandError(f"Не удалось прочитать {path}: {error}") from error
        run = import_feed(supplier, parse_rows(records, supplier.columns), timezone.now())
        self.stdout.write(
            f"Строк {run.rows_total}, сопоставлено {run.rows_matched}, "
            f"ждут сопоставления {run.rows_unmatched}, с ошибками {run.rows_invalid}"
        )
