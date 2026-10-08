from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.catalog.labels import variant_title
from apps.orders.services import OrderError

from .models import CLOSED_STATUSES, WarrantyCase
from .services import find_sold_unit, open_case, warranty_info


@admin.register(WarrantyCase)
class WarrantyCaseAdmin(admin.ModelAdmin):
    """Случаи открываются только через поиск по IMEI («Добавить») — там видно, действует ли гарантия."""

    list_display = ("imei", "product", "status", "opened_at", "service_center")
    list_filter = ("status",)
    search_fields = ("unit__imei1", "unit__imei2", "unit__serial", "unit__order_line__order__number")
    fields = ("device", "complaint", "service_center", "status", "note", "opened_at", "opened_by", "closed_at")
    readonly_fields = ("device", "complaint", "opened_at", "opened_by", "closed_at")

    @admin.display(description="IMEI")
    def imei(self, obj: WarrantyCase) -> str:
        return obj.unit.imei1 or obj.unit.serial

    @admin.display(description="Товар")
    def product(self, obj: WarrantyCase) -> str:
        return variant_title(obj.unit.variant)

    @admin.display(description="Устройство")
    def device(self, obj: WarrantyCase) -> str:
        info = warranty_info(obj.unit)
        until = f", гарантия до {info.until:%d.%m.%Y}" if info.until else ""
        return format_html("{} — IMEI {}, заказ {}{}", info.title, obj.unit.imei1, info.order or "—", until)

    def save_model(self, request, obj, form, change):
        if obj.status in CLOSED_STATUSES:
            obj.closed_at = obj.closed_at or timezone.now()
        else:
            obj.closed_at = None
        super().save_model(request, obj, form, change)

    def add_view(self, request, form_url="", extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        now = timezone.now()
        data = request.POST if request.method == "POST" else request.GET
        query = data.get("imei", "").strip()[:64]
        unit = find_sold_unit(query) if query else None
        info = warranty_info(unit) if unit else None
        error = ""
        if request.method == "POST" and unit is not None:
            try:
                case = open_case(unit, data.get("complaint", ""), data.get("service_center", ""), now,
                                 f"manager:{request.user.username}")
            except OrderError as failure:
                error = failure.message
            else:
                self.message_user(request, "Гарантийный случай открыт", messages.SUCCESS)
                return redirect(reverse("admin:warranty_warrantycase_change", args=[case.pk]))
        context = {
            **self.admin_site.each_context(request), "opts": self.model._meta, "title": "Гарантия по IMEI",
            "query": query, "info": info, "active": info.is_active(now) if info else False, "error": error,
        }
        return TemplateResponse(request, "admin/warranty/lookup.html", context)
