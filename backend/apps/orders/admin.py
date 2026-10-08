from django.contrib import admin, messages
from django.utils import timezone

from apps.payments.admin import PaymentInline

from .models import Order, OrderEvent, OrderLine, SupplierRequest
from .services import OrderError, cancel_order, confirm_sourcing


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    fk_name = "order"
    extra = 0
    can_delete = False
    fields = ("variant", "qty", "price_uzs", "is_gift", "offer")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    fields = ("created_at", "status_from", "status_to", "actor", "note")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class SupplierRequestInline(admin.TabularInline):
    model = SupplierRequest
    extra = 0
    can_delete = False
    fields = ("supplier", "status", "proposed_cost_usd", "sent_at", "answered_at", "alerted_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Статус меняется только действиями — через машину состояний, с записью в историю."""

    list_display = ("number", "customer", "status", "total_uzs", "created_at", "sla_deadline")
    list_filter = ("status", "payment_method")
    search_fields = ("number", "customer__phone")
    inlines = [OrderLineInline, SupplierRequestInline, PaymentInline, OrderEventInline]
    actions = ["confirm_sourcing_action", "cancel_action"]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in Order._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _apply(self, request, queryset, action, done_label: str) -> None:
        done = 0
        for order in queryset:
            try:
                action(order, timezone.now(), f"manager:{request.user.username}")
                done += 1
            except OrderError as error:
                self.message_user(request, f"{order}: {error.message}", messages.WARNING)
        if done:
            self.message_user(request, f"{done_label}: {done}")

    @admin.action(description="Подтвердить у поставщика", permissions=["change"])
    def confirm_sourcing_action(self, request, queryset):
        self._apply(request, queryset, confirm_sourcing, "Подтверждено")

    @admin.action(description="Отменить (резервы снимутся)", permissions=["change"])
    def cancel_action(self, request, queryset):
        self._apply(
            request, queryset, lambda order, now, actor: cancel_order(order, now, actor, "Отменён менеджером"),
            "Отменено",
        )
