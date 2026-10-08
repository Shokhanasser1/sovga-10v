from rest_framework import serializers

from .models import Brand, Category, ProductModel, Status, Variant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name_ru", "name_uz", "parent", "is_serialized"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["slug", "name"]


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ["sku", "axes", "attributes", "images", "giftable"]


class ProductListSerializer(serializers.ModelSerializer):
    brand = BrandSerializer()
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = ProductModel
        fields = ["slug", "name_ru", "name_uz", "brand", "category", "is_accessory"]


class ProductDetailSerializer(ProductListSerializer):
    variants = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description_ru", "description_uz", "attributes",
            "seo_title_ru", "seo_title_uz", "seo_description_ru", "seo_description_uz",
            "variants",
        ]

    def get_variants(self, obj: ProductModel) -> list[dict]:
        active = [variant for variant in obj.variants.all() if variant.status == Status.ACTIVE]
        return VariantSerializer(active, many=True).data


class ComparisonRowSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()
    values = serializers.ListField(child=serializers.JSONField())
    best = serializers.ListField(child=serializers.IntegerField())
