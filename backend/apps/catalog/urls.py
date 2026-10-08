from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="categories"),
    path("products/", views.ProductListView.as_view(), name="products"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path(
        "products/<slug:slug>/accessories/",
        views.AccessoriesView.as_view(),
        name="product-accessories",
    ),
    path("compare/", views.CompareView.as_view(), name="compare"),
    path("search/suggest/", views.SuggestView.as_view(), name="search-suggest"),
    path("facets/", views.FacetsView.as_view(), name="facets"),
    path("sitemap/", views.SitemapView.as_view(), name="sitemap"),
]
