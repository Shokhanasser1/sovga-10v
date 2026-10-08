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

from . import payme


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
