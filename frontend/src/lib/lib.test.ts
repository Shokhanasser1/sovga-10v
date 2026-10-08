import { describe, expect, it } from "vitest";

import { apiUrl } from "./api-client";
import { COMPARE_KEY, addToCompare, readCompare, removeFromCompare, type CompareItem } from "./compare-store";
import { deliveryText, formatPriceFrom, formatSum, formatValue } from "./format";
import { formatDate } from "./navigation";
import { getDictionary, isLocale, localized, pluralRu, switchLocalePath } from "./i18n";

const NBSP = " ";

class MemoryStorage {
  private data = new Map<string, string>();
  getItem(key: string) {
    return this.data.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
}

function item(sku: string, category = "smartphones"): CompareItem {
  return { sku, slug: sku.toLowerCase(), category, name_ru: sku, name_uz: sku, variantLabel: "" };
}

describe("formatSum", () => {
  it("groups thousands with non-breaking spaces and adds the currency", () => {
    expect(formatSum(14_020_000, "ru")).toBe(`14${NBSP}020${NBSP}000${NBSP}сум`);
    expect(formatSum(150_000, "uz")).toBe(`150${NBSP}000${NBSP}soʻm`);
  });

  it("puts «от» before the price in Russian and «dan» after it in Uzbek", () => {
    expect(formatPriceFrom(990_000, "ru")).toBe(`от${NBSP}990${NBSP}000${NBSP}сум`);
    expect(formatPriceFrom(990_000, "uz")).toBe(`990${NBSP}000${NBSP}soʻmdan`);
  });
});

describe("formatValue", () => {
  it("formats numbers with localized units", () => {
    expect(formatValue(256, "ГБ", "ru")).toBe(`256${NBSP}ГБ`);
    expect(formatValue(256, "ГБ", "uz")).toBe(`256${NBSP}GB`);
    expect(formatValue(6.3, "″", "ru")).toBe("6,3″");
  });

  it("translates booleans and enum codes", () => {
    expect(formatValue(true, "", "uz")).toBe("Ha");
    expect(formatValue("black", "", "ru")).toBe("Чёрный");
    expect(formatValue("Snapdragon 8 Elite", "", "ru")).toBe("Snapdragon 8 Elite");
  });
});

describe("deliveryText", () => {
  it("describes when the order arrives", () => {
    expect(deliveryText("in_stock", 0, "ru")).toBe("В наличии — доставим сегодня");
    expect(deliveryText("on_order", 3, "ru")).toBe("Под заказ — доставим за 3 дня");
    expect(deliveryText("in_stock", 1, "uz")).toBe("Mavjud — ertaga yetkazamiz");
    expect(deliveryText("out_of_stock", null, "ru")).toBe("Нет в наличии");
  });
});

describe("i18n", () => {
  it("knows supported locales", () => {
    expect(isLocale("ru")).toBe(true);
    expect(isLocale("en")).toBe(false);
  });

  it("declines Russian nouns", () => {
    expect([1, 2, 5, 11, 21, 24].map((n) => pluralRu(n, "товар", "товара", "товаров"))).toEqual([
      "товар", "товара", "товаров", "товаров", "товар", "товара",
    ]);
    expect(getDictionary("ru").found(3)).toBe("3 товара");
  });

  it("switches the language prefix and keeps the rest of the path", () => {
    expect(switchLocalePath("/ru/product/iphone-16-pro", "uz")).toBe("/uz/product/iphone-16-pro");
    expect(switchLocalePath("/ru", "uz")).toBe("/uz");
    expect(switchLocalePath("/catalog", "ru")).toBe("/ru/catalog");
  });

  it("falls back to Russian when the Uzbek name is empty", () => {
    expect(localized({ name_ru: "Чехлы", name_uz: "" }, "uz")).toBe("Чехлы");
  });
});

describe("compare store", () => {
  it("adds, deduplicates and removes items", () => {
    const store = new MemoryStorage();
    addToCompare(item("A"), store);
    addToCompare(item("B"), store);
    addToCompare(item("A"), store);

    expect(readCompare(store).map((i) => i.sku)).toEqual(["B", "A"]);
    expect(removeFromCompare("B", store).map((i) => i.sku)).toEqual(["A"]);
  });

  it("keeps at most four models, dropping the oldest", () => {
    const store = new MemoryStorage();
    for (const sku of ["A", "B", "C", "D", "E"]) addToCompare(item(sku), store);

    expect(readCompare(store).map((i) => i.sku)).toEqual(["B", "C", "D", "E"]);
  });

  it("starts a new list when a model from another category is added", () => {
    const store = new MemoryStorage();
    addToCompare(item("A"), store);

    expect(addToCompare(item("CASE", "cases"), store).map((i) => i.sku)).toEqual(["CASE"]);
  });

  it("ignores corrupted or foreign data in storage", () => {
    const store = new MemoryStorage();
    store.setItem(COMPARE_KEY, "{not json");
    expect(readCompare(store)).toEqual([]);

    store.setItem(COMPARE_KEY, JSON.stringify([{ sku: 1 }]));
    expect(readCompare(store)).toEqual([]);
  });
});

describe("apiUrl", () => {
  it("joins base, path and query without double slashes", () => {
    expect(apiUrl("/api/v1/catalog/compare/", { skus: "A,B", lang: "uz" }, "http://127.0.0.1:8000/")).toBe(
      "http://127.0.0.1:8000/api/v1/catalog/compare/?skus=A%2CB&lang=uz",
    );
  });

  it("uses a relative URL when the base is empty (production behind nginx)", () => {
    expect(apiUrl("/api/v1/pricing/products/x/", undefined, "")).toBe("/api/v1/pricing/products/x/");
  });
});

describe("formatDate", () => {
  it("keeps the calendar day in any time zone", () => {
    expect(formatDate("2027-10-08", "ru")).toContain("8");
    expect(formatDate("2027-10-08", "ru")).toContain("2027");
    expect(formatDate("2027-01-01", "ru")).not.toContain("2026");
  });
});
