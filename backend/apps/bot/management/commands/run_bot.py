import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.bot.polling import poll_once
from apps.notifications.outbox import deliver_pending
from apps.notifications.telegram import TelegramError, simulated
from apps.orders.supplier_requests import alert_silent_requests

MAX_PAUSE = 60


class Command(BaseCommand):
    help = (
        "Telegram-бот: отвечает покупателям и поставщикам и без задержки рассылает уведомления. "
        "Запускать в отдельном окне рядом с runserver и не закрывать; Ctrl+C — остановить."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--once", action="store_true", help="Один круг опроса — для проверки")

    def handle(self, *args, once: bool = False, **options) -> None:
        if simulated():
            raise CommandError("Учебный режим без токена: бот работает в админке → «Имитация Telegram», run_bot не нужен")
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("Нет TELEGRAM_BOT_TOKEN в backend/.env — бот не запущен")
        self.stdout.write("Бот запущен. Ctrl+C — остановить.")
        offset, pause = None, 1
        try:
            while True:
                try:
                    offset = poll_once(offset)
                    alert_silent_requests(timezone.now())
                    deliver_pending(timezone.now())
                    pause = 1
                except TelegramError as error:
                    self.stderr.write(f"Telegram недоступен ({error}) — повтор через {pause} с")
                    time.sleep(pause)
                    pause = min(pause * 2, MAX_PAUSE)
                if once:
                    return
        except KeyboardInterrupt:
            self.stdout.write("Бот остановлен.")
