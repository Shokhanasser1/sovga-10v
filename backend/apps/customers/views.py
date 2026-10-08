import ipaddress

from django.contrib.auth import login, logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttling import OtpRateThrottle, client_ident

from .models import Customer
from .otp import OtpError, request_code, verify_code
from .phones import normalize_uz_phone
from .senders import build_sender
from .services import AccountConflict, customer_for_phone

RATE_ERRORS = {"too_soon", "too_many"}
# Номер выданного кода в сессии: проверка идёт только по коду, запрошенному этим браузером.
CHALLENGE_KEY = "otp_challenge"


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)

    def validate_phone(self, value: str) -> str:
        phone = normalize_uz_phone(value)
        if phone is None:
            raise serializers.ValidationError("Нужен узбекский мобильный номер: +998 XX XXX XX XX")
        return phone


class VerifySerializer(PhoneSerializer):
    code = serializers.RegexField(r"^\s*\d{6}\s*$", error_messages={"invalid": "Код — 6 цифр"})


def customer_payload(customer: Customer | None) -> dict | None:
    if customer is None:
        return None
    address = customer.addresses.first()  # последний использованный
    return {
        "phone": customer.phone, "name": customer.name, "language": customer.language,
        "address": {"text": address.text, "landmark": address.landmark} if address else None,
    }


def current_customer(request) -> Customer | None:
    if not request.user.is_authenticated:
        return None
    return Customer.objects.filter(user=request.user).first()


def _ip(request) -> str | None:
    ident = client_ident(request)
    try:
        return str(ipaddress.ip_address(ident)) if ident else None
    except ValueError:
        return None


def _otp_error(error: OtpError) -> Response:
    code = status.HTTP_429_TOO_MANY_REQUESTS if error.code in RATE_ERRORS else status.HTTP_400_BAD_REQUEST
    return Response({"detail": error.message, "code": error.code}, status=code)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    """Кто вошёл; заодно выдаёт CSRF-cookie для следующих POST-запросов."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"customer": customer_payload(current_customer(request))})


@method_decorator(csrf_protect, name="dispatch")
class RequestCodeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OtpRateThrottle]

    def post(self, request):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            otp = request_code(
                serializer.validated_data["phone"], timezone.now(), build_sender(),
                ip=_ip(request), previous_id=request.session.get(CHALLENGE_KEY),
            )
        except OtpError as error:
            return _otp_error(error)
        request.session[CHALLENGE_KEY] = otp.pk
        return Response({"sent": True, "channel": otp.channel, "resend_after": 60})


@method_decorator(csrf_protect, name="dispatch")
class VerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OtpRateThrottle]

    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        try:
            verify_code(
                phone, serializer.validated_data["code"], timezone.now(),
                challenge_id=request.session.get(CHALLENGE_KEY),
            )
        except OtpError as error:
            return _otp_error(error)
        try:
            customer = customer_for_phone(phone)
        except AccountConflict as error:
            return Response({"detail": str(error), "code": "conflict"}, status=status.HTTP_409_CONFLICT)
        request.session.pop(CHALLENGE_KEY, None)
        login(request, customer.user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"customer": customer_payload(customer)})


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
