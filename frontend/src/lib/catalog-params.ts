/** Параметры каталога: из адресной строки в запрос к API и обратно в ссылки. */

export type SearchParams = Record<string, string | string[] | undefined>;

const PASSED = new Set(["q", "brand", "price_min", "price_max", "available", "sort", "page"]);
const MAX_LENGTH = 200;

function joined(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value.join(",") : (value ?? "")).slice(0, MAX_LENGTH);
}

/** Только известные параметры; повторяющиеся (brand=a&brand=b) склеиваются через запятую. */
export function toApiParams(searchParams: SearchParams, category?: string): Record<string, string> {
  const params: Record<string, string> = {};
  for (const [key, value] of Object.entries(searchParams)) {
    const text = joined(value).trim();
    if (text && (PASSED.has(key) || key.startsWith("f."))) params[key] = text;
  }
  if (category) params.category = category;
  return params;
}

export function selectedValues(searchParams: SearchParams, key: string): Set<string> {
  return new Set(joined(searchParams[key]).split(",").filter(Boolean));
}

export function pageHref(path: string, searchParams: SearchParams, page: number): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(toApiParams(searchParams))) {
    if (key !== "page") query.set(key, value);
  }
  if (page > 1) query.set("page", String(page));
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}
