from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    path("request-code/", views.RequestCodeView.as_view(), name="request-code"),
    path("verify/", views.VerifyView.as_view(), name="verify"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
]
