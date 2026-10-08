/** Список сравнения в localStorage: до 4 вариантов одной категории. */

import { z } from "zod";

export const COMPARE_KEY = "sovga:compare:v1";
export const COMPARE_LIMIT = 4;
const CHANGE_EVENT = "sovga:compare-change";

const compareItemSchema = z.object({
  sku: z.string().min(1).max(64),
  slug: z.string().min(1).max(200),
  category: z.string().min(1).max(100),
  name_ru: z.string().max(200),
  name_uz: z.string().max(200),
  variantLabel: z.string().max(200),
});

export type CompareItem = z.infer<typeof compareItemSchema>;

type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function parseCompare(raw: string | null): CompareItem[] {
  if (!raw) return [];
  try {
    const parsed = z.array(compareItemSchema).safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data.slice(0, COMPARE_LIMIT) : [];
  } catch {
    return [];
  }
}

export function readCompare(store: Storage | null = storage()): CompareItem[] {
  if (!store) return [];
  try {
    return parseCompare(store.getItem(COMPARE_KEY));
  } catch {
    return [];
  }
}

function write(items: CompareItem[], store: Storage | null): void {
  if (!store) return;
  try {
    store.setItem(COMPARE_KEY, JSON.stringify(items));
  } catch {
    return;
  }
  if (typeof window !== "undefined") window.dispatchEvent(new Event(CHANGE_EVENT));
}

/**
 * Добавить вариант. Модель другой категории начинает новый список,
 * переполненный список вытесняет самую старую модель.
 */
export function addToCompare(item: CompareItem, store: Storage | null = storage()): CompareItem[] {
  const current = readCompare(store).filter(
    (existing) => existing.sku !== item.sku && existing.category === item.category,
  );
  const next = [...current, item].slice(-COMPARE_LIMIT);
  write(next, store);
  return next;
}

export function removeFromCompare(sku: string, store: Storage | null = storage()): CompareItem[] {
  const next = readCompare(store).filter((item) => item.sku !== sku);
  write(next, store);
  return next;
}

export function subscribeCompare(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const onStorage = (event: StorageEvent) => {
    if (event.key === COMPARE_KEY) callback();
  };
  window.addEventListener(CHANGE_EVENT, callback);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGE_EVENT, callback);
    window.removeEventListener("storage", onStorage);
  };
}
