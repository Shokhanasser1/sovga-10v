/**
 * Запросы из браузера — напрямую в Django, без посредничества Next.js: так Django видит адрес
 * каждого посетителя и считает лимит запросов отдельно. В проде NEXT_PUBLIC_API_URL пустой —
 * nginx отдаёт /api/ этого же сайта в Django.
 *
 * Вход по коду держится на cookie сессии Django, поэтому запросы идут с credentials: "include",
 * а POST несут CSRF-токен из cookie csrftoken. Локально витрина и API должны быть на одном имени
 * хоста (localhost:3000 и localhost:8000), иначе браузер не отправит cookie.
 */

import { z } from "zod";

import {
  codeSentSchema,
  comparisonRowSchema,
  meSchema,
  orderSchema,
  quoteSchema,
  suggestSchema,
  variantOfferSchema,
  type ComparisonRow,
  type Customer,
  type Order,
  type Quote,
  type Suggestions,
  type VariantOffer,
} from "./schemas";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

export function apiUrl(path: string, query?: Record<string, string>, base: string = API_BASE): string {
  const search = query ? `?${new URLSearchParams(query)}` : "";
  return `${base.replace(/\/$/, "")}${path}${search}`;
}

export function csrfFromCookie(cookie: string): string {
  const match = cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function firstMessage(value: unknown): string | undefined {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(firstMessage).find(Boolean);
  if (value && typeof value === "object") return Object.values(value).map(firstMessage).find(Boolean);
  return undefined;
}

/** Ошибка DRF → одно понятное сообщение для покупателя. */
export function errorMessage(data: unknown, status: number): string {
  if (status === 429 && !(data && typeof data === "object" && "code" in data)) {
    return "Слишком много запросов. Подождите минуту и попробуйте снова.";
  }
  return firstMessage(data) ?? `Магазин ответил ошибкой ${status}`;
}

type RequestOptions = { method?: "GET" | "POST"; body?: unknown; signal?: AbortSignal };

async function request<T>(path: string, schema: z.ZodType<T>, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method === "POST") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfFromCookie(document.cookie);
  }
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      credentials: "include",
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiClientError("Нет связи с магазином. Проверьте интернет.", 0);
  }
  const data: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const code = data && typeof data === "object" && "code" in data ? String(data.code) : undefined;
    throw new ApiClientError(errorMessage(data, response.status), response.status, code);
  }
  const parsed = schema.safeParse(data);
  if (!parsed.success) throw new ApiClientError("Магазин прислал данные в неожиданном формате", response.status);
  return parsed.data;
}

/** Перед первым POST получаем CSRF-cookie. */
async function ensureCsrf(): Promise<void> {
  if (!csrfFromCookie(document.cookie)) await fetchMe();
}

async function post<T>(path: string, schema: z.ZodType<T>, body: unknown = {}): Promise<T> {
  await ensureCsrf();
  return request(path, schema, { method: "POST", body });
}

export function fetchSuggestions(query: string, signal?: AbortSignal): Promise<Suggestions> {
  return request(`/api/v1/catalog/search/suggest/?${new URLSearchParams({ q: query })}`, suggestSchema, { signal });
}

export function fetchOffers(slug: string): Promise<VariantOffer[]> {
  return request(`/api/v1/pricing/products/${encodeURIComponent(slug)}/`, z.array(variantOfferSchema));
}

export function fetchComparison(skus: string[], lang: string): Promise<ComparisonRow[]> {
  const query = new URLSearchParams({ skus: skus.join(","), lang });
  return request(`/api/v1/catalog/compare/?${query}`, z.array(comparisonRowSchema));
}

export async function fetchDemo(): Promise<boolean> {
  return (await request("/api/v1/demo/", z.object({ demo: z.boolean() }))).demo;
}

export async function fetchMe(): Promise<Customer | null> {
  return (await request("/api/v1/auth/me/", meSchema)).customer;
}

export function requestCode(phone: string) {
  return post("/api/v1/auth/request-code/", codeSentSchema, { phone });
}

export async function verifyCode(phone: string, code: string): Promise<Customer | null> {
  return (await post("/api/v1/auth/verify/", meSchema, { phone, code })).customer;
}

export async function logout(): Promise<void> {
  await post("/api/v1/auth/logout/", z.null());
}

export type CartRequestItem = { sku: string; qty: number; gift_sku?: string | null };

export function fetchQuote(items: CartRequestItem[], signal?: AbortSignal): Promise<Quote> {
  return ensureCsrf().then(() =>
    request("/api/v1/orders/quote/", quoteSchema, { method: "POST", body: { items, payment_method: "card" }, signal }),
  );
}

export function createOrder(body: {
  items: CartRequestItem[];
  address: { text: string; landmark: string };
  comment: string;
}): Promise<Order> {
  return post("/api/v1/orders/", orderSchema, { ...body, payment_method: "card" });
}

export function fetchOrders(): Promise<Order[]> {
  return request("/api/v1/orders/", z.array(orderSchema));
}

export function fetchOrder(number: string): Promise<Order> {
  return request(`/api/v1/orders/${encodeURIComponent(number)}/`, orderSchema);
}

export function cancelOrder(number: string): Promise<Order> {
  return post(`/api/v1/orders/${encodeURIComponent(number)}/cancel/`, orderSchema);
}

/** Ссылка на бота. Пустая строка — учебный режим: чат уже подключён, переписка в «Имитации Telegram». */
export async function telegramLink(lang: string): Promise<string> {
  return (await post("/api/v1/bot/link/", z.object({ url: z.string().url().or(z.literal("")) }), { lang })).url;
}

export async function payLink(number: string, provider: "payme" | "click", lang: string): Promise<string> {
  const response = await post(`/api/v1/orders/${encodeURIComponent(number)}/pay/`, z.object({ url: z.string().url() }), {
    provider,
    lang,
  });
  return response.url;
}
