import pytest
from django.core.management import CommandError, call_command

from apps.bot.dispatch import handle_update
from apps.bot.links import customer_link, supplier_link
from apps.bot.polling import poll_once
from apps.orders.quote import CartItem
from apps.orders.services import DeliveryAddress, create_order

from .conftest import NOW, message, start_payload

pytestmark = pytest.mark.django_db
CHAT = 555


def say(text: str, chat_id: int = CHAT) -> None:
    handle_update(message(chat_id, text), NOW)


def link(customer) -> None:
    say(f"/start {start_payload(customer_link(customer, NOW))}")


def test_start_links_the_customer_and_answers_in_their_language(bot, telegram, customer):
    customer.language = "uz"
    customer.save()

    link(customer)

    customer.refresh_from_db()
    assert customer.telegram_chat_id == CHAT
    assert "Tayyor" in telegram.sent(CHAT)[-1]


def test_start_with_a_used_or_unknown_code(bot, telegram, customer):
    payload = start_payload(customer_link(customer, NOW))
    say(f"/start {payload}", chat_id=1)

    say(f"/start {payload}")

    assert "устарела" in telegram.sent(CHAT)[-1]
    customer.refresh_from_db()
    assert customer.telegram_chat_id == 1


def test_start_links_a_supplier(bot, telegram, make_supplier):
    supplier = make_supplier("Опт Чиланзар", connector_type="telegram")

    say(f"/start {start_payload(supplier_link(supplier, NOW))}")

    supplier.refresh_from_db()
    assert supplier.telegram_chat_id == CHAT
    assert "Опт Чиланзар" in telegram.sent(CHAT)[-1]


@pytest.mark.parametrize("text", ["/start", "привет", "/help"])
def test_anything_else_gets_help(bot, telegram, text):
    say(text)

    assert "/orders" in telegram.sent(CHAT)[-1]


def test_orders_lists_the_latest(bot, telegram, customer, shop):
    order = create_order(customer, [CartItem("IP16P-256-B", 1)], "card", DeliveryAddress("Ташкент"), "", NOW)
    link(customer)

    say("/orders")

    reply = telegram.sent(CHAT)[-1]
    assert order.number in reply and "Ждёт оплаты" in reply and "14 080 000 сум" in reply


def test_orders_and_stop_need_a_linked_chat(bot, telegram):
    say("/orders")
    say("/stop")

    assert all("не привязан" in text for text in telegram.sent(CHAT))


def test_stop_unlinks(bot, telegram, customer):
    link(customer)

    say("/stop")

    customer.refresh_from_db()
    assert customer.telegram_chat_id is None
    assert "Больше не присылаем" in telegram.sent(CHAT)[-1]


@pytest.mark.parametrize("command", ["/id", "/id@sovga_test_bot"])
def test_id_tells_the_chat_number(bot, telegram, command):
    say(command, chat_id=-1001234)

    assert "-1001234" in telegram.sent(-1001234)[-1]


def test_messages_without_text_are_ignored(bot, telegram):
    handle_update({"update_id": 1, "message": {"chat": {"id": CHAT}, "photo": [{}]}}, NOW)
    handle_update({"update_id": 2, "edited_message": {"chat": {"id": CHAT}, "text": "x"}}, NOW)

    assert telegram.calls == []


def test_poll_survives_a_broken_update(bot, telegram, monkeypatch):
    import apps.bot.polling as polling

    handled = []

    def flaky(update, now):
        if update["update_id"] == 7:
            raise RuntimeError("сломалось")
        handled.append(update["update_id"])

    monkeypatch.setattr(polling, "handle_update", flaky)
    telegram.updates = [message(CHAT, "a", update_id=7), message(CHAT, "b", update_id=8)]

    offset = poll_once(None)

    assert offset == 9
    assert handled == [8]
    assert "Не получилось" in telegram.sent(CHAT)[-1]
    assert "offset" not in telegram.last("getUpdates")


def test_poll_confirms_the_offset(bot, telegram):
    poll_once(42)

    assert telegram.last("getUpdates")["offset"] == 42


def test_run_bot_needs_a_token(settings):
    settings.TELEGRAM_BOT_TOKEN = ""

    with pytest.raises(CommandError):
        call_command("run_bot", "--once")


def test_run_bot_answers_and_delivers_the_outbox(bot, telegram, monkeypatch):
    from apps.notifications import outbox

    monkeypatch.setitem(outbox._HANDLERS, "ping", lambda payload: telegram("sendMessage", {"chat_id": 1, "text": "pong"}))
    outbox.emit("ping", {}, now=NOW)
    telegram.updates = [message(CHAT, "/id")]

    call_command("run_bot", "--once")

    assert str(CHAT) in telegram.sent(CHAT)[-1]
    assert telegram.sent(1) == ["pong"]
