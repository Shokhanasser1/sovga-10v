from django.contrib import admin

from apps.catalog.models import Variant
from apps.sourcing.models import Warehouse

from .models import InventoryUnit, PurchaseBatch
from .services import sync_own_offer


@admin.register(PurchaseBatch)
class PurchaseBatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "supplier", "received_at", "note")
    search_fields = ("note",)


@admin.register(InventoryUnit)
class InventoryUnitAdmin(admin.ModelAdmin):
    """Сохранение и удаление единиц сразу пересчитывают своё предложение на складе."""

    list_display = ("variant", "imei1", "serial", "warehouse", "status", "uzimei_status", "cost_usd")
    list_filter = ("status", "uzimei_status", "warehouse")
    search_fields = ("imei1", "imei2", "serial", "variant__sku")
    autocomplete_fields = ("variant", "purchase_batch")

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = (
                InventoryUnit.objects.filter(pk=obj.pk)
                .values_list("variant_id", "warehouse_id")
                .first()
            )
        super().save_model(request, obj, form, change)
        sync_own_offer(obj.variant, obj.warehouse)
        if previous and previous != (obj.variant_id, obj.warehouse_id):
            sync_own_offer(Variant.objects.get(pk=previous[0]), Warehouse.objects.get(pk=previous[1]))

    def delete_model(self, request, obj):
        variant, warehouse = obj.variant, obj.warehouse
        super().delete_model(request, obj)
        sync_own_offer(variant, warehouse)

    def delete_queryset(self, request, queryset):
        pairs = set(queryset.values_list("variant_id", "warehouse_id"))
        super().delete_queryset(request, queryset)
        for variant_id, warehouse_id in pairs:
            sync_own_offer(Variant.objects.get(pk=variant_id), Warehouse.objects.get(pk=warehouse_id))
