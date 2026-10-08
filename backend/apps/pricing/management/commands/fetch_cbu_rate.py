from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.pricing.cbu import fetch_usd_rate
from apps.pricing.models import ExchangeRate


class Command(BaseCommand):
    help = "Загрузить курс USD ЦБ Узбекистана на сегодня"

    def handle(self, *args, **options) -> None:
        rate_date, rate = fetch_usd_rate(timezone.localdate())
        obj, created = ExchangeRate.objects.update_or_create(
            date=rate_date, defaults={"cbu_rate": rate}
        )
        action = "Создан" if created else "Обновлён"
        self.stdout.write(f"{action} курс на {obj.date}: {obj.cbu_rate}")
