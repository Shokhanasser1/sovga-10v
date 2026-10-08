import { describe, expect, it } from "vitest";

import { addToCart, cartList, clearCart, readCart, removeFromCart, setCartGift, setCartQty } from "./cart-store";
import { csrfFromCookie, errorMessage } from "./api-client";

class MemoryStorage {
  private data = new Map<string, string>();
  getItem(key: string) {
    return this.data.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
}

const phone = { sku: "IP16P-256-BLK", slug: "iphone-16-pro", name_ru: "iPhone 16 Pro", name_uz: "iPhone 16 Pro", variantLabel: "256 ГБ" };

describe("cart store", () => {
  it("adds items and increases quantity up to five", () => {
    const store = new MemoryStorage();
    for (let i = 0; i < 7; i += 1) addToCart(phone, store);

    expect(readCart(store)).toEqual([{ ...phone, qty: 5 }]);
  });

  it("refuses the eleventh position", () => {
    const store = new MemoryStorage();
    for (let i = 0; i < 10; i += 1) addToCart({ ...phone, sku: `SKU-${i}` }, store);

    expect(addToCart({ ...phone, sku: "SKU-10" }, store)).toBe(false);
    expect(readCart(store)).toHaveLength(10);
  });

  it("changes quantity within limits, gift and removes items", () => {
    const store = new MemoryStorage();
    addToCart(phone, store);

    expect(setCartQty(phone.sku, 9, store)[0].qty).toBe(5);
    expect(setCartQty(phone.sku, 0, store)[0].qty).toBe(1);
    expect(setCartGift(phone.sku, null, store)[0].gift_sku).toBeNull();
    expect(setCartGift(phone.sku, "CASE-1", store)[0].gift_sku).toBe("CASE-1");
    expect(removeFromCart(phone.sku, store)).toEqual([]);
  });

  it("clears and ignores foreign data", () => {
    const store = new MemoryStorage();
    addToCart(phone, store);
    clearCart(store);
    expect(readCart(store)).toEqual([]);

    store.setItem(cartList.key, JSON.stringify([{ ...phone, qty: 99 }]));
    expect(readCart(store)).toEqual([]);
  });
});

describe("api client helpers", () => {
  it("reads the CSRF token from cookies", () => {
    expect(csrfFromCookie("theme=dark; csrftoken=abc%3D123; other=1")).toBe("abc=123");
    expect(csrfFromCookie("theme=dark")).toBe("");
  });

  it("turns DRF errors into one readable message", () => {
    expect(errorMessage({ detail: "Неверный код." }, 400)).toBe("Неверный код.");
    expect(errorMessage({ phone: ["Нужен узбекский мобильный номер"] }, 400)).toBe("Нужен узбекский мобильный номер");
    expect(errorMessage({ address: { text: ["Слишком коротко"] } }, 400)).toBe("Слишком коротко");
    expect(errorMessage({ detail: "Request was throttled." }, 429)).toBe(
      "Слишком много запросов. Подождите минуту и попробуйте снова.",
    );
    expect(errorMessage(null, 500)).toBe("Магазин ответил ошибкой 500");
  });
});

describe("safeNext", () => {
  it("allows only same-language paths of this site", async () => {
    const { safeNext } = await import("./navigation");

    expect(safeNext("/ru/checkout", "ru")).toBe("/ru/checkout");
    expect(safeNext(null, "uz")).toBe("/uz/orders");
    expect(safeNext("https://evil.example", "ru")).toBe("/ru/orders");
    expect(safeNext("//evil.example/ru/", "ru")).toBe("/ru/orders");
    expect(safeNext("/ru/\\evil", "ru")).toBe("/ru/orders");
    expect(safeNext("/uz/checkout", "ru")).toBe("/ru/orders");
  });
});
