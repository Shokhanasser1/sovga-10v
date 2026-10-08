import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.customers.senders import (
    ConsoleSender,
    DeliveryError,
    EskizSmsSender,
    FallbackSender,
    TelegramGatewaySender,
    build_sender,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def json(self):
        return self.payload


class Recorder:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_telegram_gateway_request():
    http = Recorder(FakeResponse({"ok": True, "result": {}}))

    channel = TelegramGatewaySender("tg-token", http_post=http).send("+998901234567", "123456")

    url, kwargs = http.calls[0]
    assert channel == "telegram"
    assert url == "https://gatewayapi.telegram.org/sendVerificationMessage"
    assert kwargs["headers"] == {"Authorization": "Bearer tg-token"}
    assert kwargs["json"]["phone_number"] == "+998901234567"
    assert kwargs["json"]["code"] == "123456"


def test_telegram_gateway_error():
    http = Recorder(FakeResponse({"ok": False, "error": "PHONE_NUMBER_INVALID"}))

    with pytest.raises(DeliveryError):
        TelegramGatewaySender("t", http_post=http).send("+998901234567", "123456")


def test_eskiz_logs_in_once_and_sends_sms():
    http = Recorder(
        FakeResponse({"data": {"token": "eskiz-token"}}),
        FakeResponse({"status": "waiting"}),
        FakeResponse({"status": "waiting"}),
    )
    sender = EskizSmsSender("shop@example.uz", "secret", template="Kod: {code}", http_post=http)

    assert sender.send("+998901234567", "123456") == "sms"
    sender.send("+998901234567", "654321")

    login, first, second = http.calls
    assert login[0] == "https://notify.eskiz.uz/api/auth/login"
    assert first[1]["data"] == {"mobile_phone": "998901234567", "message": "Kod: 123456", "from": "4546"}
    assert first[1]["headers"] == {"Authorization": "Bearer eskiz-token"}
    assert second[1]["data"]["message"] == "Kod: 654321"


def test_eskiz_rejected_message():
    http = Recorder(FakeResponse({"data": {"token": "t"}}), FakeResponse({"message": "bad"}, status=400))

    with pytest.raises(DeliveryError):
        EskizSmsSender("e", "p", http_post=http).send("+998901234567", "1")


class Broken:
    def send(self, phone, code):
        raise DeliveryError("нет")


class Working:
    def send(self, phone, code):
        return "sms"


def test_fallback_tries_next_channel():
    assert FallbackSender([Broken(), Working()]).send("+998901234567", "1") == "sms"
    with pytest.raises(DeliveryError):
        FallbackSender([Broken()]).send("+998901234567", "1")


def test_build_sender_without_credentials(settings):
    settings.TELEGRAM_GATEWAY_TOKEN = ""
    settings.ESKIZ_EMAIL = ""
    settings.ESKIZ_PASSWORD = ""

    settings.DEBUG = True
    assert isinstance(build_sender(), ConsoleSender)
    settings.DEBUG = False
    with pytest.raises(ImproperlyConfigured):
        build_sender()


def test_build_sender_prefers_telegram(settings):
    settings.TELEGRAM_GATEWAY_TOKEN = "t"
    settings.ESKIZ_EMAIL = "e"
    settings.ESKIZ_PASSWORD = "p"

    sender = build_sender()

    assert isinstance(sender, FallbackSender)
    assert [type(s) for s in sender.senders] == [TelegramGatewaySender, EskizSmsSender]
