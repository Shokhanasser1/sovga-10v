import { enumLabel, getDictionary, unitLabel, type Locale } from "./i18n";
import type { OrderStatus } from "./schemas";

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

/** Оплата при получении: пока курьер не отдал заказ, покупателю нужно приготовить деньги. */
export function dueOnDelivery(order: { payment_method: string; status: string }): boolean {
  return order.payment_method === "cod" && ["cod", "picking", "handed_to_carrier"].includes(order.status);
}

/** Шаг в истории заказа. При оплате курьеру «Ждёт оплаты» сбивает с толку — заказ просто принят. */
export function eventTitle(paymentMethod: string, status: OrderStatus, locale: Locale): string {
  const dict = getDictionary(locale);
  return paymentMethod === "cod" && status === "confirmed" ? dict.orderAccepted : dict.orderStatus[status];
}

/** «Чехол Spigen · Чёрный» — название и значения осей варианта (цвет и т. п.). */
export function withVariant(name: string, axes: Record<string, AttrValue>, locale: Locale): string {
  const parts = Object.values(axes).map((value) => formatValue(value, "", locale));
  return [name, ...parts].join(" · ");
}

/** Абзацы описания товара: разделитель — пустая строка. */
export function paragraphs(text: string): string[] {
  return text
    .split(/\r?\n\s*\r?\n/)
    .map((part) => part.trim())
    .filter(Boolean);
}
