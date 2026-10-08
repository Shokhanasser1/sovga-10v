from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer

from .models import Order
from .quote import quote
from .serializers import OrderCreateSerializer, QuoteRequestSerializer, order_payload, quote_payload
from .services import DeliveryAddress, OrderError, cancel_order, create_order


class IsCustomer(BasePermission):
    """Вошёл покупатель (у сотрудника без профиля покупателя заказов нет)."""

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and Customer.objects.filter(user=request.user).exists()


def _customer(request) -> Customer:
    return Customer.objects.get(user=request.user)


def own_order(request, number: str) -> Order:
    return get_object_or_404(Order, number=number, customer__user=request.user)


class QuoteView(APIView):
    """Расчёт корзины: цены, наличие, подарки. Ничего не сохраняет."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = quote(serializer.cart(), serializer.validated_data["payment_method"], timezone.now())
        return Response(quote_payload(result))


class OrderListCreateView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        orders = Order.objects.filter(customer__user=request.user).select_related("customer").prefetch_related("events")[:50]
        return Response([order_payload(order) for order in orders])

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        address = DeliveryAddress(data["address"]["text"], data["address"]["landmark"])
        try:
            order = create_order(
                _customer(request), serializer.cart(), data["payment_method"], address, data["comment"], timezone.now()
            )
        except OrderError as error:
            return Response({"detail": error.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(order_payload(order), status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request, number: str):
        return Response(order_payload(own_order(request, number)))


class OrderCancelView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, number: str):
        order = own_order(request, number)
        try:
            order = cancel_order(order, timezone.now(), actor=f"customer:{order.customer.phone}", by_customer=True)
        except OrderError as error:
            return Response({"detail": error.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(order_payload(order))
