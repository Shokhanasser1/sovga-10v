import { enumLabel, getDictionary, unitLabel, type Locale } from "./i18n";

export type AttrValue = string | number | boolean;

const NBSP = " ";
const numberFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });

export function formatNumber(value: number): string {
  return numberFormat.format(value).replace(/\s/g, NBSP);
}

/** 14020000 → «14 020 000 сум» / «14 020 000 soʻm». */
export function formatSum(amount: number, locale: Locale): string {
  return `${formatNumber(amount)}${NBSP}${locale === "uz" ? "soʻm" : "сум"}`;
}

/** Цена «от» в листинге: «от 14 020 000 сум» / «14 020 000 soʻmdan». */
export function formatPriceFrom(amount: number, locale: Locale): string {
  return locale === "uz" ? `${formatSum(amount, locale)}dan` : `от${NBSP}${formatSum(amount, locale)}`;
}

export function formatValue(value: AttrValue, unit: string, locale: Locale): string {
  if (typeof value === "boolean") {
    const dict = getDictionary(locale);
    return value ? dict.yes : dict.no;
  }
  if (typeof value === "number") {
    const text = formatNumber(value);
    if (!unit) return text;
    return unit === "″" ? `${text}″` : `${text}${NBSP}${unitLabel(unit, locale)}`;
  }
  return enumLabel(value, locale);
}

export type AvailabilityStatus = "in_stock" | "on_order" | "out_of_stock";

export function deliveryText(
  status: AvailabilityStatus,
  leadDays: number | null,
  locale: Locale,
): string {
  const dict = getDictionary(locale);
  if (status === "out_of_stock" || leadDays === null) return dict.outOfStock;
  const label = status === "in_stock" ? dict.inStock : dict.onOrder;
  const when =
    leadDays === 0 ? dict.deliveryToday : leadDays === 1 ? dict.deliveryTomorrow : dict.deliveryIn(leadDays);
  return `${label} — ${when}`;
}
