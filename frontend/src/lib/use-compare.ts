"use client";

import { useMemo, useSyncExternalStore } from "react";

import { cartList, type CartItem } from "./cart-store";
import { compareList, type CompareItem } from "./compare-store";

function useLocalList<T>(list: { snapshot: () => string; subscribe: (cb: () => void) => () => void; parse: (raw: string | null) => T[] }): T[] {
  const raw = useSyncExternalStore(list.subscribe, list.snapshot, () => "");
  return useMemo(() => list.parse(raw), [list, raw]);
}

/** Текущий список сравнения; обновляется при изменении в этой и других вкладках. */
export function useCompare(): CompareItem[] {
  return useLocalList(compareList);
}

/** Текущая корзина; обновляется при изменении в этой и других вкладках. */
export function useCart(): CartItem[] {
  return useLocalList(cartList);
}
