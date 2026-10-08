from django.contrib import admin

from .models import (
    AccessoryCompat,
    AttributeDefinition,
    Brand,
    Category,
    CompatRule,
    ProductModel,
    Variant,
)


class AttributeDefinitionInline(admin.TabularInline):
    model = AttributeDefinition
    extra = 0
    fields = (
        "code", "name_ru", "name_uz", "type", "unit", "enum_values", "level",
        "is_variant_axis", "is_required", "is_facet", "comparison", "sort_order",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "slug", "parent", "is_serialized")
    search_fields = ("name_ru", "name_uz", "slug")
    inlines = [AttributeDefinitionInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class VariantInline(admin.StackedInline):
    model = Variant
    extra = 0
    fields = (
        "sku", "axes", "attributes", "mxik_code", "package_code", "barcodes",
        "weight_g", "images", "giftable", "status",
    )


class AccessoryCompatInline(admin.TabularInline):
    model = AccessoryCompat
    fk_name = "accessory"
    extra = 0
    autocomplete_fields = ("device",)
    verbose_name_plural = "Совместимые устройства (явно)"


class CompatRuleInline(admin.TabularInline):
    model = CompatRule
    extra = 0
    verbose_name_plural = "Правила совместимости"


@admin.register(ProductModel)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "brand", "category", "is_accessory", "status")
    list_filter = ("status", "is_accessory", "category", "brand")
    search_fields = ("name_ru", "name_uz", "slug")
    autocomplete_fields = ("category", "brand")
    inlines = [VariantInline, AccessoryCompatInline, CompatRuleInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product_model", "status", "giftable")
    list_filter = ("status", "giftable")
    search_fields = ("sku", "product_model__name_ru")
    autocomplete_fields = ("product_model",)
