from django.contrib import admin

from .models import ExchangeRate, MarkupRule, PriceSnapshot


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("date", "cbu_rate", "spread_pct", "effective_rate")
    date_hierarchy = "date"


@admin.register(MarkupRule)
class MarkupRuleAdmin(admin.ModelAdmin):
    list_display = ("__str__", "markup_pct", "min_margin_uzs", "rounding_step_uzs", "is_active")
    list_filter = ("is_active",)
    autocomplete_fields = ("variant", "category", "brand")


@admin.register(PriceSnapshot)
class PriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("variant", "price_uzs", "cost_usd", "rate", "computed_at")
    search_fields = ("variant__sku",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
