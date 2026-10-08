from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from apps.delivery.models import Shipment
from apps.payments.admin import PaymentInline

from . import desk
from .models import OperatorDesk, Order, OrderEvent, OrderLine, ReturnRequest, SupplierRequest
from .services import OrderError, cancel_order, confirm_sourcing


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    fk_name = "order"
    extra = 0
    can_delete = False
    fields = ("variant", "qty", "price_uzs", "is_gift", "offer")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    fields = ("created_at", "status_from", "status_to", "actor", "note")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class SupplierRequestInline(admin.TabularInline):
    model = SupplierRequest
    extra = 0
    can_delete = False
    fields = ("supplier", "status", "proposed_cost_usd", "sent_at", "answered_at", "alerted_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0
    can_delete = False
    fields = ("carrier", "courier_name", "courier_phone", "service_name", "tracking", "cost_uzs", "handed_at",
              "delivered_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class ReturnRequestInline(admin.StackedInline):
    model = ReturnRequest
    extra = 0
    can_delete = False
    fields = ("status", "reason", "imeis_received", "gift_returned", "refund_amount_uzs", "note", "created_at",
              "inspected_at", "refunded_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Статус меняется только действиями — через машину состояний, с записью в историю."""

    list_display = ("number", "customer", "status", "total_uzs", "created_at", "sla_deadline")
    list_filter = ("status", "payment_method")
    search_fields = ("number", "customer__phone")
    inlines = [
        OrderLineInline, SupplierRequestInline, PaymentInline, ShipmentInline, ReturnRequestInline, OrderEventInline,
    ]
    actions = ["confirm_sourcing_action", "cancel_action"]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in Order._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _apply(self, request, queryset, action, done_label: str) -> None:
        done = 0
        for order in queryset:
            try:
                action(order, timezone.now(), f"manager:{request.user.username}")
                done += 1
            except OrderError as error:
                self.message_user(request, f"{order}: {error.message}", messages.WARNING)
        if done:
            self.message_user(request, f"{done_label}: {done}")

    @admin.action(description="Подтвердить у поставщика", permissions=["change"])
    def confirm_sourcing_action(self, request, queryset):
        self._apply(request, queryset, confirm_sourcing, "Подтверждено")

    @admin.action(description="Отменить (резервы снимутся)", permissions=["change"])
    def cancel_action(self, request, queryset):
        self._apply(
            request, queryset, lambda order, now, actor: cancel_order(order, now, actor, "Отменён менеджером"),
            "Отменено",
        )


@admin.register(OperatorDesk)
class OperatorDeskAdmin(admin.ModelAdmin):
    """Очередь заказов по этапам и страница сборки. Доступ — у кого есть право изменять заказы."""

    def _allowed(self, request) -> bool:
        return request.user.is_active and request.user.has_perm("orders.change_order")

    def has_module_permission(self, request):
        return self._allowed(request)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path("<str:number>/pick/", view(self.pick_view), name="orders_operatordesk_pick"),
            path("<str:number>/do/<str:action>/", view(self.action_view), name="orders_operatordesk_action"),
        ] + super().get_urls()

    def _render(self, request, template: str, context: dict) -> TemplateResponse:
        if not self._allowed(request):
            raise PermissionDenied
        context = {**self.admin_site.each_context(request), "opts": self.model._meta, **context}
        return TemplateResponse(request, template, context)

    def changelist_view(self, request, extra_context=None):
        if not self._allowed(request):
            raise PermissionDenied
        now = timezone.now()
        query = request.GET.get("q", "").strip()[:40]
        found = desk.find_orders(query) if query else []
        if len(found) == 1:
            return redirect(reverse("admin:orders_operatordesk_pick", args=[found[0].number]))
        return self._render(request, "admin/orders/operator_desk.html", {
            "title": "Рабочее место оператора", "sections": desk.sections(now), "now": now,
            "query": query, "found": found,
        })

    def pick_view(self, request, number: str):
        order = get_object_or_404(Order.objects.select_related("customer"), number=number)
        return self._render(request, "admin/orders/operator_pick.html", {
            "title": f"Заказ {order.number}", **desk.pick_context(order, timezone.now()),
        })

    def action_view(self, request, number: str, action: str):
        if not self._allowed(request):
            raise PermissionDenied
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        order = get_object_or_404(Order, number=number)
        try:
            message, target = desk.perform(order, action, request.POST, timezone.now(), f"manager:{request.user.username}")
        except OrderError as error:
            self.message_user(request, error.message, messages.ERROR)
            target = "pick"
        else:
            self.message_user(request, message)
        if target == "desk":
            return redirect(reverse("admin:orders_operatordesk_changelist"))
        return redirect(reverse("admin:orders_operatordesk_pick", args=[order.number]))
