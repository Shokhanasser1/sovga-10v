/** Запросы из браузера. Идут на тот же адрес /api/…, Next.js проксирует их в Django. */

import { z } from "zod";

import { comparisonRowSchema, suggestSchema, variantOfferSchema, type ComparisonRow, type Suggestions, type VariantOffer } from "./schemas";

async function getJson<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("Нет связи с магазином");
  }
  if (!response.ok) throw new Error(`Магазин ответил ошибкой ${response.status}`);
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) throw new Error("Магазин прислал данные в неожиданном формате");
  return parsed.data;
}

export function fetchSuggestions(query: string, signal?: AbortSignal): Promise<Suggestions> {
  return getJson(`/api/v1/catalog/search/suggest?q=${encodeURIComponent(query)}`, suggestSchema, signal);
}

export function fetchOffers(slug: string): Promise<VariantOffer[]> {
  return getJson(`/api/v1/pricing/products/${encodeURIComponent(slug)}`, z.array(variantOfferSchema));
}

export function fetchComparison(skus: string[], lang: string): Promise<ComparisonRow[]> {
  const query = new URLSearchParams({ skus: skus.join(","), lang });
  return getJson(`/api/v1/catalog/compare?${query}`, z.array(comparisonRowSchema));
}
