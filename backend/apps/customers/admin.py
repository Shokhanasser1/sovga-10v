from django.contrib import admin

from .models import Address, Customer, OtpCode


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("phone", "name", "language", "created_at")
    search_fields = ("phone", "name")
    readonly_fields = ("user", "phone", "created_at")
    inlines = [AddressInline]

    def has_add_permission(self, request):
        return False  # покупатель появляется при первом входе по коду


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "channel", "created_at", "expires_at", "attempts", "consumed_at", "ip")
    search_fields = ("phone",)
    exclude = ("code_hash",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
