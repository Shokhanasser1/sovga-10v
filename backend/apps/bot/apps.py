from django.apps import AppConfig


class BotConfig(AppConfig):
    name = "apps.bot"

    def ready(self) -> None:
        from . import handlers  # noqa: F401 — регистрирует обработчики outbox
