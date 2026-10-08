from django.apps import AppConfig


class BotConfig(AppConfig):
    name = "apps.bot"

    def ready(self) -> None:
        from apps.notifications.telegram import use_demo_transport

        from . import demo, handlers  # noqa: F401 — handlers регистрирует обработчики outbox

        use_demo_transport(demo.transport)  # учебный режим без токена — «Имитация Telegram»
