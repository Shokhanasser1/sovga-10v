from django.urls import path

from apps.payments.views import PayLinkView

from . import views

app_name = "orders"

urlpatterns = [
    path("quote/", views.QuoteView.as_view(), name="quote"),
    path("", views.OrderListCreateView.as_view(), name="list"),
    path("<str:number>/", views.OrderDetailView.as_view(), name="detail"),
    path("<str:number>/cancel/", views.OrderCancelView.as_view(), name="cancel"),
    path("<str:number>/pay/", PayLinkView.as_view(), name="pay"),
]
