from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    name = "apps.payments"

    def ready(self) -> None:
        from . import handlers  # noqa: F401 — регистрирует обработчики outbox
