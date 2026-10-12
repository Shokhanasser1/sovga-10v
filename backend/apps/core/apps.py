from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _roles_after_migrate(sender, **kwargs) -> None:
    # Права приложения появляются в его post_migrate — роли пересобираем после каждого, это дёшево.
    from .staff import apply_roles

    apply_roles()


class CoreConfig(AppConfig):
    name = "apps.core"

    def ready(self) -> None:
        post_migrate.connect(_roles_after_migrate, dispatch_uid="sovga_staff_roles")
