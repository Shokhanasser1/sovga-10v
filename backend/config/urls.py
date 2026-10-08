from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/pricing/", include("apps.pricing.urls")),
    path("api/v1/auth/", include("apps.customers.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/bot/", include("apps.bot.urls")),
]
