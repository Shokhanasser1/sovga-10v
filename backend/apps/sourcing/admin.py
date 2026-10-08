from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .matching import confirm_match, suggest_variants, variant_label
from .models import (
    Offer,
    Reservation,
    Supplier,
    SupplierFeedRow,
    SupplierFeedRun,
    SupplierSkuMap,
    Warehouse,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Записи создаёт система, руками их не добавляют и не правят."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "connector_type", "reliability", "lead_time_days", "bot_connected", "is_active")
    list_filter = ("connector_type", "is_active")
    search_fields = ("name",)
    readonly_fields = ("telegram_chat_id",)
    actions = ["bot_link_action"]

    @admin.display(description="Бот", boolean=True)
    def bot_connected(self, obj: Supplier) -> bool:
        return obj.telegram_chat_id is not None

    @admin.action(description="Ссылка для подключения Telegram-бота", permissions=["change"])
    def bot_link_action(self, request, queryset):
        from apps.bot.demo import supplier_chat
        from apps.bot.links import supplier_link
        from apps.notifications.telegram import bot_available, simulated

        if simulated():
            for supplier in queryset:
                supplier.telegram_chat_id = supplier_chat(supplier)
                supplier.save(update_fields=["telegram_chat_id"])
            self.message_user(request, "Учебный режим: поставщики подключены к учебным чатам — см. «Имитация Telegram»")
            return
        if not bot_available():
            self.message_user(
                request, "Бот не настроен: нужны TELEGRAM_BOT_TOKEN и TELEGRAM_BOT_USERNAME в backend/.env",
                messages.WARNING,
            )
            return
        for supplier in queryset:
            self.message_user(
                request,
                f"{supplier}: отправьте поставщику ссылку {supplier_link(supplier, timezone.now())} — "
                "она действует 24 часа и открывается один раз",
            )


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "is_active")
    search_fields = ("name",)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "variant", "source", "cost_usd", "qty_available", "lead_time_days",
        "last_confirmed_at", "is_active",
    )
    list_filter = ("is_active", "supplier", "warehouse")
    search_fields = ("variant__sku", "variant__product_model__name_ru")
    autocomplete_fields = ("variant", "supplier", "warehouse")

    @admin.display(description="Источник")
    def source(self, obj: Offer):
        return obj.warehouse or obj.supplier


@admin.register(SupplierSkuMap)
class SupplierSkuMapAdmin(admin.ModelAdmin):
    list_display = ("supplier", "supplier_code", "variant")
    list_filter = ("supplier",)
    search_fields = ("supplier_code", "variant__sku")
    autocomplete_fields = ("supplier", "variant")


@admin.register(SupplierFeedRun)
class SupplierFeedRunAdmin(ReadOnlyAdmin):
    list_display = (
        "supplier", "started_at", "rows_total", "rows_matched", "rows_unmatched",
        "rows_invalid", "error",
    )
    list_filter = ("supplier",)


@admin.register(SupplierFeedRow)
class SupplierFeedRowAdmin(admin.ModelAdmin):
    """Очередь сопоставления: выберите SKU — код запомнится, предложение появится сразу."""

    list_display = ("supplier_code", "name", "price_usd", "qty", "status", "supplier")
    list_filter = ("status", "run__supplier")
    search_fields = ("supplier_code", "name")
    fields = (
        "supplier", "supplier_code", "name", "price_usd", "qty", "status", "error",
        "suggestions", "variant",
    )
    readonly_fields = (
        "supplier", "supplier_code", "name", "price_usd", "qty", "status", "error", "suggestions",
    )
    autocomplete_fields = ("variant",)

    def has_add_permission(self, request):
        return False

    @admin.display(description="Поставщик")
    def supplier(self, obj: SupplierFeedRow):
        return obj.run.supplier

    @admin.display(description="Подсказки")
    def suggestions(self, obj: SupplierFeedRow):
        found = suggest_variants(obj.name or obj.supplier_code)
        if not found:
            return "—"
        return format_html_join(
            mark_safe("<br>"),
            "{} — {} ({}%)",
            ((variant.sku, variant_label(variant), round(score * 100)) for variant, score in found),
        )

    def save_model(self, request, obj, form, change):
        if "variant" in form.changed_data and obj.variant is not None:
            confirm_match(obj, obj.variant)
            messages.success(request, f"Код {obj.supplier_code} привязан к {obj.variant.sku}")
        else:
            super().save_model(request, obj, form, change)


@admin.register(Reservation)
class ReservationAdmin(ReadOnlyAdmin):
    list_display = ("ref", "offer", "qty", "is_soft", "expires_at", "released_at")
    list_filter = ("is_soft",)
    search_fields = ("ref",)
