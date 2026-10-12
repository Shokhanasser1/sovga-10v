"""Сквозная проверка витрины в настоящем браузере.

Что нужно запущенным — в учебном режиме, без единого ключа (start.cmd из папки scripts делает всё сам):
  1. Django с демо-данными и DEMO_MODE=true: код входа — на экране, оплата — страница «Учебная оплата»
  2. Витрина: из frontend/ — npm run build, затем npm start
Запуск: python e2e/storefront_check.py   (адреса — переменные STOREFRONT_URL и API_URL)
Скриншоты сохраняются в e2e/shots/.
"""

import os
import random
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
BASE = os.environ.get("STOREFRONT_URL", "http://localhost:3000").rstrip("/")
API = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
# Свой номер на каждый прогон: лимиты на номер (раз в минуту, 5 в час) не мешают повторным прогонам.
BUYER_PHONE = f"90 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
problems: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("OK   " if condition else "FAIL ") + message)
    if not condition:
        problems.append(message)


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
    check(page.locator("#catalog a").count() >= 8, "главная: все восемь категорий")
    check(page.get_by_text("Учебный магазин").count() == 1, "учебный режим: плашка на витрине")

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
    check(page.get_by_role("heading", name="Описание").count() == 1 and "титановом корпусе" in page.content(),
          "карточка: описание товара")
    page.get_by_role("button", name="512").click()
    page.wait_for_timeout(300)
    price_after = page.locator("[aria-live=polite] .price").inner_text()
    check(price_after != price_before, f"смена варианта меняет цену: {price_before} → {price_after}")
    check(page.get_by_role("button", name="Титан").get_attribute("aria-pressed") == "true",
          "512 ГБ есть только в титане — цвет переключился сам")
    page.get_by_role("button", name="Сравнить").click()
    check(page.get_by_role("note").count() == 0, "карточка: без предупреждения eSIM у обычной версии")
    page.get_by_role("button", name="Только eSIM").click()
    page.wait_for_timeout(300)
    check("физическую SIM-карту вставить нельзя" in page.get_by_role("note").inner_text(), "карточка: предупреждение «Только eSIM»")

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

    # Покупка целиком: карточка → корзина с подарком → вход по коду с экрана → оформление → учебная оплата.
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
    buyer.wait_for_function("/^\\d{6}$/.test(document.querySelector('input[autocomplete=one-time-code]')?.value ?? '')",
                            timeout=10000)
    check(buyer.get_by_text("Учебный режим: SMS не отправляется").count() == 1, "вход: код показан на экране и подставлен")
    buyer.get_by_role("button", name="Войти").click()
    buyer.wait_for_url("**/ru/checkout", timeout=10000)
    number = place_order(buyer, screenshot="10-checkout.png")
    buyer.screenshot(path=OUT / "11-order.png", full_page=True)
    check(buyer.get_by_text("подарок", exact=True).count() >= 1, "заказ: подарок в составе")
    check(buyer.locator("header").get_by_text("Корзина").inner_text().strip() == "Корзина", "корзина очищена после заказа")
    check(buyer.get_by_role("button", name="Оплатить через Payme").count() == 1, "заказ: кнопка оплаты Payme")

    # Учебный режим: чат подключается сразу, переписка — в админке «Имитация Telegram».
    buyer.get_by_role("button", name="Получать статусы в Telegram").click()
    buyer.wait_for_selector("text=Статусы заказа приходят в Telegram", timeout=10000)
    check(True, "заказ: учебный чат Telegram подключён")

    # Учебная оплата: магазин получает те же запросы Payme, что от настоящего провайдера.
    buyer.get_by_role("button", name="Оплатить через Payme").click()
    buyer.wait_for_url(f"**/api/v1/payments/demo/payme/{number}/**", timeout=10000)
    buyer.screenshot(path=OUT / "12-demo-payment.png", full_page=True)
    check("Учебная оплата" in buyer.content() and "не списываются" in buyer.content(), "учебная оплата: страница имитации")
    buyer.get_by_role("button", name="Оплатить", exact=True).click()
    buyer.wait_for_url(f"**/ru/orders/{number}", timeout=10000)
    buyer.wait_for_selector("text=Оплачен", timeout=10000)
    buyer.screenshot(path=OUT / "13-paid.png", full_page=True)
    check(buyer.get_by_role("button", name="Отменить заказ").count() == 0, "оплаченный заказ покупатель сам не отменяет")
    check(buyer.get_by_role("button", name="Оплатить через Payme").count() == 0, "оплаченный заказ: кнопок оплаты нет")
    # «Провайдер вернул деньги»: заказ отменяется, резерв снимается — повторные прогоны снова находят товар.
    buyer.goto(f"{API}/api/v1/payments/demo/payme/{number}/?lang=ru")
    buyer.get_by_role("button", name="Провайдер вернул деньги").click()
    buyer.wait_for_url(f"**/ru/orders/{number}", timeout=10000)
    buyer.wait_for_selector("text=Отменён", timeout=10000)
    check(True, "учебная оплата: возврат денег отменил заказ")

    # Второй заказ: покупатель уже вошёл — сразу оформление, затем отмена.
    open_cart(buyer)
    buyer.get_by_role("link", name="Оформить заказ").click()
    buyer.wait_for_url("**/ru/checkout", timeout=10000)
    buyer.wait_for_function("document.querySelector('#address').value !== ''", timeout=10000)
    check(buyer.get_by_label("Адрес доставки").input_value() == "Ташкент, Юнусабад 4-12, кв. 7",
          "повторный заказ: адрес подставлен из прошлого")
    place_order(buyer)
    buyer.get_by_role("button", name="Отменить заказ").click()
    buyer.wait_for_selector("text=Отменён", timeout=10000)
    check(buyer.get_by_role("button", name="Отменить заказ").count() == 0, "заказ отменён покупателем")

    real_errors = [e for e in errors if "favicon" not in e and "404" not in e]
    check(not real_errors, f"ошибки в консоли: {real_errors[:3]}")
    browser.close()

print(f"\nСкриншоты: {OUT}")
sys.exit(1 if problems else 0)
