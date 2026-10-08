from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sourcing.fetch import URL_CONNECTORS, sync_supplier
from apps.sourcing.models import Supplier


class Command(BaseCommand):
    help = "Загрузить прайсы активных поставщиков по ссылке (Google Sheets CSV / JSON API)"

    def handle(self, *args, **options) -> None:
        now = timezone.now()
        suppliers = Supplier.objects.filter(
            is_active=True, connector_type__in=URL_CONNECTORS
        ).exclude(feed_url="")
        for supplier in suppliers:
            run = sync_supplier(supplier, now)
            if run.error:
                self.stderr.write(f"{supplier}: {run.error}")
            else:
                self.stdout.write(
                    f"{supplier}: строк {run.rows_total}, сопоставлено {run.rows_matched}, "
                    f"ждут сопоставления {run.rows_unmatched}, с ошибками {run.rows_invalid}"
                )
