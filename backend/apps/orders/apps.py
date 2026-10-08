from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"

    def ready(self) -> None:
        from . import handlers  # noqa: F401 — регистрирует обработчики outbox
