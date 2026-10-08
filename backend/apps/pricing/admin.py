from django.contrib import admin

from .models import ExchangeRate, MarkupRule


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("date", "cbu_rate", "spread_pct", "effective_rate")
    date_hierarchy = "date"


@admin.register(MarkupRule)
class MarkupRuleAdmin(admin.ModelAdmin):
    list_display = ("__str__", "markup_pct", "min_margin_uzs", "rounding_step_uzs", "is_active")
    list_filter = ("is_active",)
    autocomplete_fields = ("variant", "category", "brand")
