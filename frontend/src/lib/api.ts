/** Запросы к Django API со стороны сервера. Выполняются только во время запроса посетителя. */

import "server-only";

import { connection } from "next/server";
import { cache } from "react";
import { z } from "zod";

import {
  categorySchema,
  facetsSchema,
  pageSchema,
  productDetailSchema,
  productSummarySchema,
  variantOfferSchema,
  type Category,
  type Facets,
  type Page,
  type ProductDetail,
  type ProductSummary,
  type VariantOffer,
} from "./schemas";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
// Общий секрет с Django: серверные запросы витрины не попадают под лимит частоты.
const INTERNAL_HEADERS: HeadersInit = process.env.INTERNAL_API_TOKEN
  ? { "X-Internal-Token": process.env.INTERNAL_API_TOKEN }
  : {};

export class ApiError extends Error {}

type Params = Record<string, string | undefined>;

async function get<T>(path: string, schema: z.ZodType<T>, params: Params = {}): Promise<T | null> {
  await connection();
  const url = new URL(path, API_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value) url.searchParams.set(key, value);
  }
  let response: Response;
  try {
    response = await fetch(url, { headers: INTERNAL_HEADERS });
  } catch {
    throw new ApiError("Сервер магазина недоступен");
  }
  if (response.status === 404) return null;
  if (!response.ok) throw new ApiError(`Сервер магазина ответил ошибкой ${response.status}`);
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) throw new ApiError("Сервер магазина прислал данные в неожиданном формате");
  return parsed.data;
}

const productPage = pageSchema(productSummarySchema);

export async function getCategories(): Promise<Category[]> {
  return (await get("/api/v1/catalog/categories/", z.array(categorySchema))) ?? [];
}

export async function getProducts(params: Params): Promise<Page<ProductSummary> | null> {
  return get("/api/v1/catalog/products/", productPage, params);
}

export async function getFacets(params: Params): Promise<Facets | null> {
  return get("/api/v1/catalog/facets/", facetsSchema, params);
}

/** Один запрос на страницу: метаданные и сама карточка берут товар отсюда. */
export const getProduct = cache(async (slug: string): Promise<ProductDetail | null> =>
  get(`/api/v1/catalog/products/${encodeURIComponent(slug)}/`, productDetailSchema),
);

export async function getOffers(slug: string): Promise<VariantOffer[]> {
  return (await get(`/api/v1/pricing/products/${encodeURIComponent(slug)}/`, z.array(variantOfferSchema))) ?? [];
}

const sitemapSchema = z.object({ categories: z.array(z.string()), products: z.array(z.string()) });

export async function getSitemap(): Promise<z.infer<typeof sitemapSchema>> {
  return (await get("/api/v1/catalog/sitemap/", sitemapSchema)) ?? { categories: [], products: [] };
}

export async function getAccessories(slug: string): Promise<ProductSummary[]> {
  const page = await get(`/api/v1/catalog/products/${encodeURIComponent(slug)}/accessories/`, productPage);
  return page?.results ?? [];
}
