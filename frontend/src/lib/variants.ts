/** Матрица вариантов: оси, состояние кнопок и переход к ближайшему существующему варианту. */

import { formatValue, type AttrValue } from "./format";
import type { Locale } from "./i18n";
import type { ProductDetail, Variant, VariantOffer } from "./schemas";

export type Axis = {
  code: string;
  name_ru: string;
  name_uz: string;
  unit: string;
  values: AttrValue[];
};

export type OptionState = "selected" | "available" | "other-combination";

function ordered(values: AttrValue[]): AttrValue[] {
  const unique = [...new Set(values)];
  return unique.every((value) => typeof value === "number")
    ? (unique as number[]).toSorted((a, b) => a - b)
    : unique;
}

export function axesOf(product: ProductDetail): Axis[] {
  return product.attribute_definitions
    .filter((definition) => definition.is_variant_axis)
    .map((definition) => ({
      code: definition.code,
      name_ru: definition.name_ru,
      name_uz: definition.name_uz,
      unit: definition.unit,
      values: ordered(product.variants.map((variant) => variant.axes[definition.code]).filter((v) => v !== undefined)),
    }))
    .filter((axis) => axis.values.length > 0);
}

function matchesOthers(variant: Variant, current: Variant, axes: Axis[], skip: string): number {
  return axes.filter((axis) => axis.code !== skip && variant.axes[axis.code] === current.axes[axis.code]).length;
}

export function optionState(variants: Variant[], current: Variant, axes: Axis[], code: string, value: AttrValue): OptionState {
  if (current.axes[code] === value) return "selected";
  const exact = variants.some(
    (variant) => variant.axes[code] === value && matchesOthers(variant, current, axes, code) === axes.length - 1,
  );
  return exact ? "available" : "other-combination";
}

/** Вариант с выбранным значением, максимально похожий на текущий; при равенстве — тот, что в наличии. */
export function chooseValue(
  variants: Variant[],
  current: Variant,
  axes: Axis[],
  code: string,
  value: AttrValue,
  offers: Record<string, VariantOffer> | null,
): Variant {
  const inStock = (variant: Variant) => (offers?.[variant.sku]?.availability.status === "out_of_stock" ? 0 : 1);
  const candidates = variants.filter((variant) => variant.axes[code] === value);
  return candidates.reduce<Variant | undefined>((best, variant) => {
    if (!best) return variant;
    const score = [matchesOthers(variant, current, axes, code), inStock(variant)];
    const bestScore = [matchesOthers(best, current, axes, code), inStock(best)];
    return score[0] > bestScore[0] || (score[0] === bestScore[0] && score[1] > bestScore[1]) ? variant : best;
  }, undefined) ?? current;
}

export function variantLabel(variant: Variant, axes: Axis[], lang: Locale): string {
  return axes
    .filter((axis) => variant.axes[axis.code] !== undefined)
    .map((axis) => formatValue(variant.axes[axis.code], axis.unit, lang))
    .join(" · ");
}
