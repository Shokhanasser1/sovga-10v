"""Сквозная проверка витрины в настоящем браузере.

Что нужно запущенным:
  1. Django с демо-данными: из backend/ — manage.py seed_demo, затем manage.py runserver
  2. Витрина: из frontend/ — npm run build, затем npm start
Запуск: python e2e/storefront_check.py   (адрес витрины — переменная STOREFRONT_URL)
Скриншоты сохраняются в e2e/shots/.
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
BASE = os.environ.get("STOREFRONT_URL", "http://localhost:3000").rstrip("/")
problems: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("OK   " if condition else "FAIL ") + message)
    if not condition:
        problems.append(message)


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

    real_errors = [e for e in errors if "favicon" not in e and "404" not in e]
    check(not real_errors, f"ошибки в консоли: {real_errors[:3]}")
    browser.close()

print(f"\nСкриншоты: {OUT}")
sys.exit(1 if problems else 0)
