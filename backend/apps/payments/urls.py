from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("payme/", views.PaymeView.as_view(), name="payme"),
]
