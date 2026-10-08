"""Сквозная проверка витрины в настоящем браузере.

Что нужно запущенным:
  1. Django с демо-данными: из backend/ — manage.py seed_demo, затем manage.py runserver
     с DEBUG=true, OTP_FIXED_CODE=000000 (код входа для проверки оформления заказа),
     PAYME_MERCHANT_ID=e2e и PAYME_KEY=e2e-payme-key (скрипт сам играет роль Payme)
  2. Витрина: из frontend/ — npm run build, затем npm start
Запуск: python e2e/storefront_check.py   (адреса — переменные STOREFRONT_URL и API_URL)
Скриншоты сохраняются в e2e/shots/.
"""

import base64
import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
BASE = os.environ.get("STOREFRONT_URL", "http://localhost:3000").rstrip("/")
API = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
OTP_CODE = os.environ.get("E2E_OTP_CODE", "000000")
PAYME_KEY = os.environ.get("E2E_PAYME_KEY", "e2e-payme-key")
# Свой номер на каждый прогон: лимиты на номер (раз в минуту, 5 в час) не мешают повторным прогонам.
BUYER_PHONE = f"90 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
problems: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("OK   " if condition else "FAIL ") + message)
    if not condition:
        problems.append(message)


def payme(method: str, params: dict) -> dict:
    """Запрос от имени Payme к нашему Merchant API — как это делает их сервер после оплаты картой."""
    auth = base64.b64encode(f"Paycom:{PAYME_KEY}".encode()).decode()
    request = urllib.request.Request(
        f"{API}/api/v1/payments/payme/",
        data=json.dumps({"id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def open_cart(page) -> None:
    page.goto(f"{BASE}/ru/product/iphone-16-pro")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Купить").click()
    page.wait_for_url("**/ru/cart", timeout=10000)
    try:
        page.wait_for_selector("input[type=radio]:checked", timeout=15000)
    except Exception:
        page.screenshot(path=OUT / "9-cart-failed.png", full_page=True)
        raise


def place_order(page, screenshot: str = "") -> str:
    """Заполняет адрес на оформлении, подтверждает и ждёт страницу заказа. Возвращает номер заказа."""
    page.get_by_label("Адрес доставки").fill("Ташкент, Юнусабад 4-12, кв. 7")
    page.get_by_label("Ориентир для курьера").fill("напротив школы №110")
    page.wait_for_function("!document.querySelector('button[type=submit]').disabled", timeout=10000)
    if screenshot:
        page.screenshot(path=OUT / screenshot, full_page=True)
    page.get_by_role("button", name="Подтвердить заказ").click()
    page.wait_for_url("**/ru/orders/SG*", timeout=15000)
    page.wait_for_selector("text=Ждёт оплаты", timeout=10000)
    return page.url.rstrip("/").rsplit("/", 1)[1]


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    page.goto(f"{BASE}/ru")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=OUT / "1-home.png", full_page=True)
    check(page.get_by_role("heading", level=1).inner_text().startswith("Каждый смартфон"), "главная: заголовок")
    check(page.locator("#catalog a").count() >= 5, "главная: категории загрузились")

    box = page.get_by_role("combobox")
    box.fill("айфон")
    page.wait_for_selector("[role=option]", timeout=5000)
    page.screenshot(path=OUT / "2-autocomplete.png")
    options = page.locator("[role=option]").all_inner_texts()
    check(any("iPhone 16 Pro" in o for o in options), f"автокомплит «айфон»: {options[:3]}")
    box.press("ArrowDown")
    box.press("Enter")
    page.wait_for_url("**/product/**", timeout=10000)
    page.wait_for_load_state("networkidle")

    page.goto(f"{BASE}/ru/product/iphone-16-pro")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("text=сум", timeout=10000)
    page.screenshot(path=OUT / "3-product.png", full_page=True)
    price_before = page.locator("[aria-live=polite] .price").inner_text()
    check("сум" in price_before, f"карточка: цена {price_before}")
    check(page.get_by_text("Подарок до").count() == 1, "карточка: лента подарка")
    check(page.get_by_text("Характеристики").count() == 1, "карточка: характеристики")
    page.get_by_role("button", name="512").click()
    page.wait_for_timeout(300)
    price_after = page.locator("[aria-live=polite] .price").inner_text()
    check(price_after != price_before, f"смена варианта меняет цену: {price_before} → {price_after}")
    check(page.get_by_role("button", name="Титан").get_attribute("aria-pressed") == "true",
          "512 ГБ есть только в титане — цвет переключился сам")
    page.get_by_role("button", name="Сравнить").click()

    page.goto(f"{BASE}/ru/product/galaxy-s25-ultra")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Сравнить").click()
    page.goto(f"{BASE}/ru/compare")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("tbody tr", timeout=10000)
    page.screenshot(path=OUT / "4-compare.png", full_page=True)
    check(page.locator("tbody tr").count() >= 5, "сравнение: строки характеристик")
    check(page.locator("td[class*=best]").count() >= 3, "сравнение: подсвечены лучшие значения")

    page.goto(f"{BASE}/ru/catalog/smartphones")
    page.wait_for_load_state("networkidle")
    total = page.locator("main li a[href*='/product/']").count()
    page.get_by_label("Титан").check()
    page.wait_for_url("**f.color=titanium**", timeout=10000)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=OUT / "5-catalog-filtered.png", full_page=True)
    filtered = page.locator("main li a[href*='/product/']").count()
    check(0 < filtered < total, f"фильтр «Титан»: {total} → {filtered}")

    page.goto(f"{BASE}/uz/product/iphone-16-pro")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("text=soʻm", timeout=10000)
    page.screenshot(path=OUT / "6-product-uz.png", full_page=True)
    check(page.get_by_text("Xususiyatlari").count() == 1, "узбекский: заголовок характеристик")

    page.goto(f"{BASE}/en")
    check(page.url.endswith("/ru/en") and "Такой страницы нет" in page.content(), f"неизвестный язык → 404 ({page.url})")
    page.goto(f"{BASE}/catalog/smartphones")
    check(page.url.endswith("/ru/catalog/smartphones"), f"адрес без языка → /ru ({page.url})")

    sitemap = page.request.get(f"{BASE}/sitemap.xml").text()
    check("/ru/product/iphone-16-pro" in sitemap and 'hreflang="uz"' in sitemap, "sitemap.xml: товары и ссылки на uz")
    page.goto(f"{BASE}/ru/product/iphone-16-pro")
    page.wait_for_load_state("networkidle")
    ld = page.locator('script[type="application/ld+json"]').first.inner_text()
    check('"priceCurrency":"UZS"' in ld and '"@type":"Product"' in ld, "JSON-LD Product с ценой в сумах")
    check(page.title().startswith("iPhone 16 Pro"), f"заголовок страницы товара: {page.title()}")

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
    mobile.goto(f"{BASE}/ru")
    mobile.wait_for_load_state("networkidle")
    mobile.screenshot(path=OUT / "7-home-mobile.png", full_page=True)
    width = mobile.evaluate("document.documentElement.scrollWidth")
    check(width <= 390, f"мобильный: нет горизонтальной прокрутки ({width}px)")
    mobile.goto(f"{BASE}/ru/product/iphone-16-pro")
    mobile.wait_for_load_state("networkidle")
    mobile.screenshot(path=OUT / "8-product-mobile.png", full_page=True)

    # Покупка целиком: карточка → корзина с подарком → вход по коду → оформление → оплата через Payme.
    buyer = browser.new_context(viewport={"width": 1366, "height": 900}).new_page()
    buyer.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    open_cart(buyer)
    buyer.screenshot(path=OUT / "9-cart.png", full_page=True)
    gift = buyer.locator("input[type=radio]:checked").locator("xpath=..").inner_text()
    check("Чехол" in gift, f"корзина: подарок выбран сам ({gift.strip()[:40]})")
    buyer.get_by_role("link", name="Оформить заказ").click()
    buyer.wait_for_url("**/ru/login?next=**", timeout=10000)
    buyer.get_by_label("Номер телефона").fill(BUYER_PHONE)
    buyer.get_by_role("button", name="Получить код").click()
    buyer.get_by_label("Код из сообщения").fill(OTP_CODE)
    buyer.get_by_role("button", name="Войти").click()
    buyer.wait_for_url("**/ru/checkout", timeout=10000)
    number = place_order(buyer, screenshot="10-checkout.png")
    buyer.screenshot(path=OUT / "11-order.png", full_page=True)
    check(buyer.get_by_text("подарок", exact=True).count() >= 1, "заказ: подарок в составе")
    check(buyer.locator("header").get_by_text("Корзина").inner_text().strip() == "Корзина", "корзина очищена после заказа")
    check(buyer.get_by_role("button", name="Оплатить через Payme").count() == 1, "заказ: кнопка оплаты Payme")

    total = buyer.context.request.get(f"{API}/api/v1/orders/{number}/").json()["total_uzs"]
    account = {"order_id": number}
    transaction = f"e2e-{random.randint(10**8, 10**9)}"
    allowed = payme("CheckPerformTransaction", {"amount": total * 100, "account": account})
    created = payme("CreateTransaction", {"id": transaction, "time": int(time.time() * 1000), "amount": total * 100, "account": account})
    performed = payme("PerformTransaction", {"id": transaction})
    check(allowed.get("result", {}).get("allow") is True and "detail" in allowed["result"], f"Payme: можно платить, чек с ИКПУ ({allowed})")
    check(created.get("result", {}).get("state") == 1, f"Payme: транзакция создана ({created})")
    check(performed.get("result", {}).get("state") == 2, f"Payme: транзакция проведена ({performed})")
    buyer.reload()
    buyer.wait_for_selector("text=Оплачен", timeout=10000)
    buyer.screenshot(path=OUT / "12-paid.png", full_page=True)
    check(buyer.get_by_role("button", name="Отменить заказ").count() == 0, "оплаченный заказ покупатель сам не отменяет")
    check(buyer.get_by_role("button", name="Оплатить через Payme").count() == 0, "оплаченный заказ: кнопок оплаты нет")
    # Возврат через Payme отменяет заказ и снимает резерв — повторные прогоны снова находят товар на складе.
    refunded = payme("CancelTransaction", {"id": transaction, "reason": 5})
    check(refunded.get("result", {}).get("state") == -2, f"Payme: возврат проведён ({refunded})")
    buyer.reload()
    buyer.wait_for_selector("text=Отменён", timeout=10000)

    # Второй заказ: покупатель уже вошёл — сразу оформление, затем отмена.
    open_cart(buyer)
    buyer.get_by_role("link", name="Оформить заказ").click()
    buyer.wait_for_url("**/ru/checkout", timeout=10000)
    place_order(buyer)
    buyer.get_by_role("button", name="Отменить заказ").click()
    buyer.wait_for_selector("text=Отменён", timeout=10000)
    check(buyer.get_by_role("button", name="Отменить заказ").count() == 0, "заказ отменён покупателем")

    real_errors = [e for e in errors if "favicon" not in e and "404" not in e]
    check(not real_errors, f"ошибки в консоли: {real_errors[:3]}")
    browser.close()

print(f"\nСкриншоты: {OUT}")
sys.exit(1 if problems else 0)
