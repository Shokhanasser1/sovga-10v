/**
 * Запросы из браузера — напрямую в Django, без посредничества Next.js: так Django видит адрес
 * каждого посетителя и считает лимит запросов отдельно. В проде NEXT_PUBLIC_API_URL пустой —
 * nginx отдаёт /api/ этого же сайта в Django.
 */

import { z } from "zod";

import { comparisonRowSchema, suggestSchema, variantOfferSchema, type ComparisonRow, type Suggestions, type VariantOffer } from "./schemas";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export function apiUrl(path: string, query?: Record<string, string>, base: string = API_BASE): string {
  const search = query ? `?${new URLSearchParams(query)}` : "";
  return `${base.replace(/\/$/, "")}${path}${search}`;
}

async function getJson<T>(url: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("Нет связи с магазином");
  }
  if (response.status === 429) throw new Error("Слишком много запросов. Подождите минуту и попробуйте снова.");
  if (!response.ok) throw new Error(`Магазин ответил ошибкой ${response.status}`);
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) throw new Error("Магазин прислал данные в неожиданном формате");
  return parsed.data;
}

export function fetchSuggestions(query: string, signal?: AbortSignal): Promise<Suggestions> {
  return getJson(apiUrl("/api/v1/catalog/search/suggest/", { q: query }), suggestSchema, signal);
}

export function fetchOffers(slug: string): Promise<VariantOffer[]> {
  return getJson(apiUrl(`/api/v1/pricing/products/${encodeURIComponent(slug)}/`), z.array(variantOfferSchema));
}

export function fetchComparison(skus: string[], lang: string): Promise<ComparisonRow[]> {
  return getJson(apiUrl("/api/v1/catalog/compare/", { skus: skus.join(","), lang }), z.array(comparisonRowSchema));
}
