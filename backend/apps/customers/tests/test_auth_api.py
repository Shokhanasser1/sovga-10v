import pytest
from django.test import Client

pytestmark = pytest.mark.django_db

BASE = "/api/v1/auth"
ORIGIN = "http://localhost:3000"


class FakeSender:
    def __init__(self):
        self.codes = []

    def send(self, phone, code):
        self.codes.append(code)
        return "fake"


@pytest.fixture
def sender(monkeypatch):
    fake = FakeSender()
    monkeypatch.setattr("apps.customers.views.build_sender", lambda: fake)
    return fake


@pytest.fixture
def browser():
    """Клиент как браузер: проверка CSRF включена, запросы идут с адреса витрины."""
    client = Client(enforce_csrf_checks=True, HTTP_ORIGIN=ORIGIN)
    client.get(f"{BASE}/me/")
    return client


def post(client, path, data):
    token = client.cookies["csrftoken"].value
    return client.post(f"{BASE}/{path}/", data, content_type="application/json", HTTP_X_CSRFTOKEN=token)


def test_me_is_anonymous_and_sets_csrf_cookie(browser):
    response = browser.get(f"{BASE}/me/")

    assert response.json() == {"customer": None}
    assert "csrftoken" in browser.cookies


def test_full_login_and_logout(browser, sender):
    assert post(browser, "request-code", {"phone": "90 123 45 67"}).json() == {
        "sent": True, "channel": "fake", "resend_after": 60,
    }

    response = post(browser, "verify", {"phone": "+998901234567", "code": sender.codes[0]})

    assert response.status_code == 200
    assert response.json()["customer"]["phone"] == "+998901234567"
    assert browser.get(f"{BASE}/me/").json()["customer"]["phone"] == "+998901234567"
    assert post(browser, "logout", {}).status_code == 204
    assert browser.get(f"{BASE}/me/").json() == {"customer": None}


def test_csrf_token_is_required(browser, sender):
    response = browser.post(f"{BASE}/request-code/", {"phone": "901234567"}, content_type="application/json")

    assert response.status_code == 403
    assert sender.codes == []


def test_invalid_phone(browser, sender):
    response = post(browser, "request-code", {"phone": "+7 900 000 00 00"})

    assert response.status_code == 400
    assert "phone" in response.json()


def test_wrong_code(browser, sender):
    post(browser, "request-code", {"phone": "901234567"})
    wrong = "000000" if sender.codes[0] != "000000" else "111111"

    response = post(browser, "verify", {"phone": "901234567", "code": wrong})

    assert response.status_code == 400
    assert response.json()["code"] == "wrong"
    assert browser.get(f"{BASE}/me/").json() == {"customer": None}


def test_resend_too_soon_is_429(browser, sender):
    post(browser, "request-code", {"phone": "901234567"})

    response = post(browser, "request-code", {"phone": "901234567"})

    assert response.status_code == 429
    assert response.json()["code"] == "too_soon"
