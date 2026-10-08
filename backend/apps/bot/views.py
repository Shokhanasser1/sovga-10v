from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer
from apps.notifications.telegram import bot_available
from apps.orders.views import IsCustomer

from .links import customer_link


class LinkSerializer(serializers.Serializer):
    lang = serializers.ChoiceField(choices=Customer.Language.choices)


class TelegramLinkView(APIView):
    """Ссылка «Получать статусы в Telegram»; язык сайта становится языком сообщений бота."""

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = LinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not bot_available():
            return Response({"detail": "Telegram-бот временно недоступен"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        customer = Customer.objects.get(user=request.user)
        customer.language = serializer.validated_data["lang"]
        customer.save(update_fields=["language"])
        return Response({"url": customer_link(customer, timezone.now())})
