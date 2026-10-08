import requests
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.search import rebuild_search_index
from apps.notifications.outbox import deliver_pending
from apps.orders.services import expire_orders
from apps.pricing.listing import refresh_listing_cache
from apps.pricing.models import ExchangeRate
from apps.pricing.repricing import reprice_all
from apps.sourcing.reservations import release_expired


class Command(BaseCommand):
    help = (
        "Периодические задачи — запускать каждые 15–30 минут (Планировщик заданий Windows / cron): "
        "прайсы поставщиков, курс ЦБ, пересчёт цен, снятие просроченных резервов, "
        "просроченные заказы, поисковый индекс, кэш листинга и доставка событий"
    )

    def handle(self, *args, **options) -> None:
        call_command("import_supplier_feeds", stdout=self.stdout, stderr=self.stderr)
        try:
            call_command("fetch_cbu_rate", stdout=self.stdout, stderr=self.stderr)
        except (requests.RequestException, ValueError) as error:
            self.stderr.write(f"Курс ЦБ не обновлён, работаем по последнему: {error}")
        now = timezone.now()
        rate = ExchangeRate.objects.order_by("-date").first()
        if rate is None:
            self.stderr.write("Нет ни одного курса — цены не пересчитаны")
        else:
            result = reprice_all(rate, now)
            self.stdout.write(
                f"Цены: изменено {result.changed}, без предложения {result.unpriced}"
            )
            if result.missing_rule:
                self.stderr.write("Нет правила наценки для: " + ", ".join(result.missing_rule))
        self.stdout.write(f"Отменено просроченных заказов: {expire_orders(now)}")
        self.stdout.write(f"Снято просроченных резервов: {release_expired(now)}")
        self.stdout.write(f"Поисковый индекс: {rebuild_search_index()} товаров")
        self.stdout.write(f"Кэш листинга: {refresh_listing_cache(now)} товаров")
        delivered = deliver_pending(now)
        self.stdout.write(
            f"События: доставлено {delivered.done}, отложено {delivered.retried}, не удалось {delivered.failed}"
        )
