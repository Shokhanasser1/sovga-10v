from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("payme/", views.PaymeView.as_view(), name="payme"),
    path("click/prepare/", views.ClickPrepareView.as_view(), name="click-prepare"),
    path("click/complete/", views.ClickCompleteView.as_view(), name="click-complete"),
]
