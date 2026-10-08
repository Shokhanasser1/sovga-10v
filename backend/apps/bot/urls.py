from django.urls import path

from . import views

app_name = "bot"

urlpatterns = [
    path("link/", views.TelegramLinkView.as_view(), name="link"),
]
