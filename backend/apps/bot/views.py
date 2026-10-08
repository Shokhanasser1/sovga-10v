from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer
from apps.notifications.telegram import bot_available, send_message, simulated
from apps.orders.views import IsCustomer

from . import demo, texts
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
        if simulated():  # учебный режим: сразу учебный чат, переписка — в админке «Имитация Telegram»
            customer.telegram_chat_id = demo.customer_chat(customer)
            customer.save(update_fields=["telegram_chat_id"])
            send_message(customer.telegram_chat_id, texts.for_language(customer.language)["linked"])
            return Response({"url": ""})
        return Response({"url": customer_link(customer, timezone.now())})
