from django.contrib import admin

from .models import Payment


class ReadOnlyPaymentMixin:
    """Платежи меняют только колбэки провайдеров — руками их не создают и не правят."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyPaymentMixin, admin.ModelAdmin):
    list_display = ("order", "provider", "external_id", "amount_uzs", "state", "created_at", "performed_at")
    list_filter = ("provider", "state")
    search_fields = ("order__number", "external_id")
    exclude = ("raw",)


class PaymentInline(ReadOnlyPaymentMixin, admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("provider", "external_id", "amount_uzs", "state", "created_at", "performed_at", "cancelled_at")
    readonly_fields = fields
