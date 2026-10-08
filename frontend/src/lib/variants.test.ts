import { describe, expect, it } from "vitest";

import type { ProductDetail, Variant, VariantOffer } from "./schemas";
import { axesOf, chooseValue, optionState, variantLabel } from "./variants";

function variant(sku: string, storage: number, color: string): Variant {
  return { sku, axes: { storage_gb: storage, color }, attributes: {}, images: [], giftable: false };
}

const VARIANTS = [
  variant("128-BLK", 128, "black"),
  variant("256-BLK", 256, "black"),
  variant("256-TIT", 256, "titanium"),
  variant("512-TIT", 512, "titanium"),
];

const definition = (code: string, unit = "") => ({
  code, name_ru: code, name_uz: code, unit, type: "number" as const, level: "variant" as const,
  is_variant_axis: true, comparison: "none" as const,
});

const PRODUCT = {
  variants: [...VARIANTS].reverse(),
  attribute_definitions: [
    definition("storage_gb", "ГБ"),
    definition("color"),
    { ...definition("weight_g"), is_variant_axis: false },
  ],
} as unknown as ProductDetail;

const AXES = axesOf(PRODUCT);

function offer(sku: string, status: VariantOffer["availability"]["status"]): VariantOffer {
  return { sku, price_uzs: 1, availability: { status, lead_time_days: 0 }, gift_budget_uzs: 0 };
}

describe("axesOf", () => {
  it("lists only variant axes, numbers sorted ascending", () => {
    expect(AXES.map((axis) => axis.code)).toEqual(["storage_gb", "color"]);
    expect(AXES[0].values).toEqual([128, 256, 512]);
    expect(AXES[1].values).toEqual(["titanium", "black"]);
  });
});

describe("optionState", () => {
  const current = VARIANTS[1]; // 256 black

  it("marks the current value, exact neighbours and values needing another combination", () => {
    expect(optionState(VARIANTS, current, AXES, "storage_gb", 256)).toBe("selected");
    expect(optionState(VARIANTS, current, AXES, "storage_gb", 128)).toBe("available");
    expect(optionState(VARIANTS, current, AXES, "storage_gb", 512)).toBe("other-combination");
    expect(optionState(VARIANTS, current, AXES, "color", "titanium")).toBe("available");
  });
});

describe("chooseValue", () => {
  it("keeps the other axes when the combination exists", () => {
    expect(chooseValue(VARIANTS, VARIANTS[1], AXES, "color", "titanium", null).sku).toBe("256-TIT");
  });

  it("switches other axes when the combination does not exist", () => {
    expect(chooseValue(VARIANTS, VARIANTS[0], AXES, "storage_gb", 512, null).sku).toBe("512-TIT");
  });

  it("prefers a variant in stock among equally close ones", () => {
    const offers = { "256-BLK": offer("256-BLK", "out_of_stock"), "256-TIT": offer("256-TIT", "in_stock") };

    expect(chooseValue(VARIANTS, VARIANTS[3], AXES, "storage_gb", 256, offers).sku).toBe("256-TIT");
    expect(chooseValue(VARIANTS, VARIANTS[0], AXES, "storage_gb", 256, offers).sku).toBe("256-BLK");
  });
});

describe("variantLabel", () => {
  it("formats axis values with units", () => {
    expect(variantLabel(VARIANTS[2], AXES, "ru")).toBe("256 ГБ · Титан");
  });
});
