import base64
import binascii
import hmac
import json

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.views import IsCustomer, own_order

from . import click, demo, payme
from .links import LINKS, PaymentUnavailable, simulated
from .models import Payment
from .services import PAYABLE

S = Order.Status


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
        if simulated(request.data["provider"]):
            path = reverse("payments:demo", args=[request.data["provider"], order.number])
            return Response({"url": f"{request.build_absolute_uri(path)}?lang={lang}"})
        try:
            return Response({"url": build(order, lang)})
        except PaymentUnavailable:
            return Response(
                {"detail": "Оплата этим способом временно недоступна — менеджер свяжется с вами"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


LABELS = {"pay": "Оплатить", "decline": "Отказаться от оплаты", "refund": "Провайдер вернул деньги"}


class DemoPaymentView(View):
    """Учебный режим: страница вместо Payme / Click. Только владелец заказа, действия — POST с CSRF."""

    def _order(self, request, provider: str, number: str) -> Order:
        if not simulated(provider) or not request.user.is_authenticated:
            raise Http404
        order = Order.objects.filter(number=number, customer__in=Customer.objects.filter(user=request.user)).first()
        if order is None:
            raise Http404
        return order

    def _render(self, request, provider: str, order: Order, error: str = ""):
        paid_here = Payment.objects.filter(order=order, provider=provider, state=Payment.State.PAID).exists()
        actions = [
            (action, LABELS[action]) for action in demo.ACTIONS[provider]
            if (action == "refund" and paid_here and order.status in (S.PAID, S.PICKING))
            or (action != "refund" and order.status in PAYABLE)
        ]
        return render(request, "payments/demo_checkout.html", {
            "provider_name": provider.capitalize(), "order": order, "error": error, "actions": actions,
            "total": f"{order.total_uzs:,}".replace(",", " "), "back": self._back(request, order),
        })

    def _back(self, request, order: Order) -> str:
        lang = request.GET.get("lang") if request.GET.get("lang") in ("ru", "uz") else "ru"
        return f"{settings.SITE_URL.rstrip('/')}/{lang}/orders/{order.number}"

    def get(self, request, provider: str, number: str):
        return self._render(request, provider, self._order(request, provider, number))

    def post(self, request, provider: str, number: str):
        order = self._order(request, provider, number)
        action = request.POST.get("action", "")
        if action not in demo.ACTIONS[provider]:
            raise Http404
        error = demo.SIMULATORS[provider](order, action, timezone.now())
        if error:
            order.refresh_from_db()
            return self._render(request, provider, order, error)
        return redirect(self._back(request, order))
