/** Список сравнения в localStorage: до 4 вариантов одной категории. */

import { z } from "zod";

import { browserStorage, createLocalList, type Storage } from "./local-store";

const compareItemSchema = z.object({
  sku: z.string().min(1).max(64),
  slug: z.string().min(1).max(200),
  category: z.string().min(1).max(100),
  name_ru: z.string().max(200),
  name_uz: z.string().max(200),
  variantLabel: z.string().max(200),
});

export type CompareItem = z.infer<typeof compareItemSchema>;

export const compareList = createLocalList("sovga:compare:v1", compareItemSchema, 4);
export const COMPARE_KEY = compareList.key;
export const COMPARE_LIMIT = compareList.limit;
export const parseCompare = compareList.parse;
export const subscribeCompare = compareList.subscribe;

export function readCompare(store: Storage | null = browserStorage()): CompareItem[] {
  return compareList.read(store);
}

/**
 * Добавить вариант. Модель другой категории начинает новый список,
 * переполненный список вытесняет самую старую модель.
 */
export function addToCompare(item: CompareItem, store: Storage | null = browserStorage()): CompareItem[] {
  const current = readCompare(store).filter(
    (existing) => existing.sku !== item.sku && existing.category === item.category,
  );
  return compareList.write([...current, item].slice(-COMPARE_LIMIT), store);
}

export function removeFromCompare(sku: string, store: Storage | null = browserStorage()): CompareItem[] {
  return compareList.write(readCompare(store).filter((item) => item.sku !== sku), store);
}
