from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"
    verbose_name = "Заказы"

    def ready(self) -> None:
        from . import handlers  # noqa: F401 — регистрирует обработчики outbox
