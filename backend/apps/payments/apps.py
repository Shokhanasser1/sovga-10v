from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    name = "apps.payments"
    verbose_name = "Платежи"

    def ready(self) -> None:
        from . import handlers  # noqa: F401 — регистрирует обработчики outbox
