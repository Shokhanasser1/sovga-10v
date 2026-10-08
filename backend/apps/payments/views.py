import base64
import binascii
import hmac
import json

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.views import IsCustomer, own_order

from . import click, payme
from .links import LINKS, PaymentUnavailable
from .services import PAYABLE


def _payme_authorized(request) -> bool:
    """Basic-аутентификация Payme: логин «Paycom», пароль — ключ кассы."""
    if not settings.PAYME_KEY:
        return False
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode()
    except (binascii.Error, UnicodeDecodeError):
        return False
    login, _, password = decoded.partition(":")
    return login == "Paycom" and hmac.compare_digest(password.encode(), settings.PAYME_KEY.encode())


@method_decorator(csrf_exempt, name="dispatch")
class PaymeView(View):
    """Payme всегда ждёт HTTP 200 и JSON-RPC ответ; ошибки — в поле error."""

    def post(self, request):
        if not _payme_authorized(request):
            return JsonResponse(payme.error_response(None, -32504, "Недостаточно прав", "Insufficient privileges"))
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(payme.error_response(None, -32700, "Ошибка разбора JSON", "Parse error"))
        return JsonResponse(payme.handle(body, timezone.now()))


@method_decorator(csrf_exempt, name="dispatch")
class ClickView(View):
    """Click присылает form-urlencoded запрос и ждёт JSON с кодом ошибки протокола."""

    handler = None

    def post(self, request):
        return JsonResponse(type(self).handler(request.POST.dict(), timezone.now()))


class ClickPrepareView(ClickView):
    handler = staticmethod(click.prepare)


class ClickCompleteView(ClickView):
    handler = staticmethod(click.complete)


class PayLinkView(APIView):
    """Ссылка на оплату заказа выбранным провайдером."""

    permission_classes = [IsCustomer]

    def post(self, request, number: str):
        order = own_order(request, number)
        build = LINKS.get(str(request.data.get("provider", "")))
        lang = request.data.get("lang") if request.data.get("lang") in ("ru", "uz") else "ru"
        if build is None:
            return Response({"detail": "Неизвестный способ оплаты"}, status=status.HTTP_400_BAD_REQUEST)
        if order.status not in PAYABLE:
            return Response({"detail": "Этот заказ сейчас нельзя оплатить"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response({"url": build(order, lang)})
        except PaymentUnavailable:
            return Response(
                {"detail": "Оплата этим способом временно недоступна — менеджер свяжется с вами"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
