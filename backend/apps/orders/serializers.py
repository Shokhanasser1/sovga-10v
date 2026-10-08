from rest_framework import serializers

from apps.notifications.telegram import bot_available
from apps.payments.links import configured_providers

from .models import Order
from .quote import CartItem, Quote
from .state import CUSTOMER_CANCELLABLE


class CartItemSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=64)
    qty = serializers.IntegerField(min_value=1, max_value=5)
    gift_sku = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True)

    def to_item(self, data: dict) -> CartItem:
        return CartItem(data["sku"], data["qty"], data.get("gift_sku") or None)


class QuoteRequestSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True, max_length=10)
    payment_method = serializers.ChoiceField(choices=["card", "installment"], default="card")

    def cart(self) -> list[CartItem]:
        return [CartItemSerializer().to_item(item) for item in self.validated_data["items"]]


class AddressSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=5, max_length=300)
    landmark = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class OrderCreateSerializer(QuoteRequestSerializer):
    payment_method = serializers.ChoiceField(
        choices=["card"], error_messages={"invalid_choice": "Пока доступна только оплата картой"}
    )
    address = AddressSerializer()
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


def _gift(option) -> dict | None:
    if option is None:
        return None
    return {
        "sku": option.sku, "name_ru": option.name_ru, "name_uz": option.name_uz,
        "price_uzs": option.price_uzs, "axes": option.axes,
    }


def quote_payload(result: Quote) -> dict:
    lines = []
    for line in result.lines:
        product = line.variant.product_model if line.variant else None
        lines.append(
            {
                "sku": line.sku,
                "slug": product.slug if product else None,
                "name_ru": product.name_ru if product else None,
                "name_uz": product.name_uz if product else None,
                "qty": line.qty,
                "unit_price_uzs": line.unit_price_uzs,
                "line_total_uzs": line.line_total_uzs,
                "availability": line.availability,
                "gift_budget_uzs": line.gift_budget_uzs,
                "gift_options": [_gift(option) for option in line.gift_options],
                "gift": _gift(line.gift),
                "errors": line.errors,
            }
        )
    return {"lines": lines, "total_uzs": result.total_uzs, "errors": result.errors, "can_order": result.can_order}


def order_payload(order: Order) -> dict:
    """Только то, что нужно покупателю: без себестоимости, источников и резервов."""
    lines = [
        {
            "sku": line.variant.sku,
            "slug": line.variant.product_model.slug,
            "name_ru": line.variant.product_model.name_ru,
            "name_uz": line.variant.product_model.name_uz,
            "qty": line.qty,
            "price_uzs": line.price_uzs,
            "is_gift": line.is_gift,
            "axes": line.variant.axes,
        }
        for line in order.lines.select_related("variant__product_model")
    ]
    events = [
        {"status": event.status_to, "note": event.note, "at": event.created_at.isoformat()}
        for event in order.events.all()
    ]
    return {
        "number": order.number,
        "status": order.status,
        "payment_method": order.payment_method,
        "total_uzs": order.total_uzs,
        "price_lock_until": order.price_lock_until.isoformat(),
        "created_at": order.created_at.isoformat(),
        "address_text": order.address_text,
        "address_landmark": order.address_landmark,
        "comment": order.comment,
        "can_cancel": order.status in CUSTOMER_CANCELLABLE,
        "can_pay": order.status in (Order.Status.CONFIRMED, Order.Status.AWAITING_PAYMENT),
        "pay_providers": configured_providers(),
        # Статусы в Telegram: уже приходят, можно подключить или бот не настроен.
        "telegram": "linked" if order.customer.telegram_chat_id else ("available" if bot_available() else "off"),
        "lines": lines,
        "events": events,
    }
