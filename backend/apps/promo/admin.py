from django.contrib import admin

from .models import GiftPolicy


@admin.register(GiftPolicy)
class GiftPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "brand", "budget_pct_of_net_margin", "budget_cap_uzs",
        "priority", "is_active",
    )
    list_filter = ("is_active",)
    autocomplete_fields = ("category", "brand")
