from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .comparison import compare_variants
from .compatibility import compatible_accessories
from .models import Category, ProductModel, Status, Variant
from .search import suggest
from .serializers import (
    CategorySerializer,
    ComparisonRowSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)

MAX_COMPARE = 4


class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = Category.objects.order_by("pk")


class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        queryset = (
            ProductModel.objects.filter(status=Status.ACTIVE)
            .select_related("brand", "category")
            .order_by("name_ru")
        )
        slug = self.request.query_params.get("category")
        if slug:
            category = get_object_or_404(Category, slug=slug)
            queryset = queryset.filter(category_id__in=category.subtree_ids())
        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
    queryset = (
        ProductModel.objects.filter(status=Status.ACTIVE)
        .select_related("brand", "category")
        .prefetch_related("variants")
    )


class AccessoriesView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        device = get_object_or_404(ProductModel, slug=self.kwargs["slug"], status=Status.ACTIVE)
        return compatible_accessories(device).select_related("brand", "category")


class CompareView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        skus = [sku for sku in request.query_params.get("skus", "").split(",") if sku]
        if not 2 <= len(skus) <= MAX_COMPARE:
            raise ValidationError({"skus": f"Укажите от 2 до {MAX_COMPARE} SKU через запятую"})
        found = {
            variant.sku: variant
            for variant in Variant.objects.filter(
                sku__in=skus, status=Status.ACTIVE, product_model__status=Status.ACTIVE
            ).select_related("product_model__category")
        }
        missing = [sku for sku in skus if sku not in found]
        if missing:
            raise ValidationError({"skus": f"Не найдены: {', '.join(missing)}"})
        try:
            rows = compare_variants(
                [found[sku] for sku in skus], language=request.query_params.get("lang", "ru")
            )
        except ValueError as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(ComparisonRowSerializer(rows, many=True).data)


class SuggestView(APIView):
    """Автокомплит в шапке: до 8 товаров и 3 категорий."""

    permission_classes = [AllowAny]

    def get(self, request):
        result = suggest(request.query_params.get("q", ""))
        return Response(
            {
                "products": ProductListSerializer(result["products"], many=True).data,
                "categories": CategorySerializer(result["categories"], many=True).data,
            }
        )
