from django.urls import path

from . import views

app_name = "pricing"

urlpatterns = [
    path("products/<slug:slug>/", views.ProductOffersView.as_view(), name="product-offers"),
]
