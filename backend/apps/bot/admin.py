import logging

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from apps.notifications.outbox import deliver_pending
from apps.notifications.telegram import simulated
from apps.sourcing.models import Supplier

from . import demo
from .dispatch import handle_update
from .models import DemoMessage

logger = logging.getLogger(__name__)


def _number(value: str | None) -> int:
    try:
        return int(value or "")
    except ValueError:
        raise Http404 from None


@admin.register(DemoMessage)
class TelegramSimulatorAdmin(admin.ModelAdmin):
    """«Имитация Telegram»: переписка бота по чатам; можно нажимать кнопки и отвечать от имени чата."""

    def _allowed(self, request) -> bool:
        return request.user.is_active and request.user.has_perm("bot.change_demomessage")

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
        return [path("", self.admin_site.admin_view(self.changelist_view), name="bot_demomessage_changelist")]

    def _page(self, chat: int) -> str:
        return f"{reverse('admin:bot_demomessage_changelist')}?chat={chat}"

    def changelist_view(self, request, extra_context=None):
        if not self._allowed(request):
            raise PermissionDenied
        context = {**self.admin_site.each_context(request), "opts": self.model._meta, "title": "Имитация Telegram"}
        if not simulated():
            return TemplateResponse(request, "admin/bot/simulator.html", {**context, "off": True})
        if request.method == "POST":
            return self._act(request)
        deliver_pending(timezone.now())  # уведомления из очереди — сразу в чаты
        chats = demo.chats()
        chat = _number(request.GET.get("chat")) if request.GET.get("chat") else (chats[0]["id"] if chats else None)
        history = list(DemoMessage.objects.filter(chat_id=chat).order_by("-pk")[:50])[::-1] if chat else []
        return TemplateResponse(request, "admin/bot/simulator.html", {
            **context, "chats": chats, "chat": chat, "history": history,
            "unlinked": Supplier.objects.filter(is_active=True, telegram_chat_id__isnull=True).order_by("name"),
        })

    def _act(self, request):
        action, now = request.POST.get("action"), timezone.now()
        if action == "link_supplier":
            supplier = get_object_or_404(Supplier, pk=_number(request.POST.get("supplier")))
            supplier.telegram_chat_id = demo.supplier_chat(supplier)
            supplier.save(update_fields=["telegram_chat_id"])
            return redirect(self._page(supplier.telegram_chat_id))
        chat = _number(request.POST.get("chat"))
        if action == "say":
            text = request.POST.get("text", "").strip()[:4096]
            if text:
                incoming = DemoMessage.objects.create(chat_id=chat, direction=DemoMessage.Direction.IN, text=text)
                self._deliver(request, {"message": {"message_id": incoming.pk, "chat": {"id": chat}, "text": text}}, now)
        elif action == "press":
            message = get_object_or_404(
                DemoMessage, pk=_number(request.POST.get("message")), chat_id=chat, direction=DemoMessage.Direction.OUT
            )
            button = next((b for b in message.buttons() if b["callback_data"] == request.POST.get("data")), None)
            if button is None:
                raise Http404  # нажать можно только кнопку, которая есть под сообщением
            DemoMessage.objects.create(chat_id=chat, direction=DemoMessage.Direction.IN, text=f"▶ {button['text']}")
            query = {
                "id": f"demo-{message.pk}", "from": {"id": chat}, "data": button["callback_data"],
                "message": {"message_id": message.pk, "chat": {"id": chat}, "text": message.text},
            }
            self._deliver(request, {"callback_query": query}, now)
        else:
            raise Http404
        return redirect(self._page(chat))

    def _deliver(self, request, update: dict, now) -> None:
        try:
            handle_update({"update_id": 0, **update}, now)
        except Exception:  # как в run_bot: сломанное сообщение не роняет страницу, но видно в логах
            logger.exception("Учебное сообщение не обработано")
            self.message_user(request, "Бот не смог обработать это сообщение — подробности в окне сервера", messages.ERROR)
