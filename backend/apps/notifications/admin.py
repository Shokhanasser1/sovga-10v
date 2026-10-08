from django.contrib import admin
from django.utils import timezone

from .models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("type", "status", "attempts", "next_attempt_at", "created_at", "last_error")
    list_filter = ("status", "type")
    actions = ["retry"]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in OutboxEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Повторить доставку")
    def retry(self, request, queryset):
        count = queryset.exclude(status=OutboxEvent.Status.DONE).update(
            status=OutboxEvent.Status.PENDING, attempts=0, next_attempt_at=timezone.now()
        )
        self.message_user(request, f"Поставлено в очередь: {count}")
