"use client";

import { useEffect, useState } from "react";

import { fetchQuote, type CartRequestItem } from "./api-client";
import type { CartItem } from "./cart-store";
import type { Quote } from "./schemas";

type State = { key: string; quote?: Quote; error?: string };

export function toRequestItems(items: CartItem[]): CartRequestItem[] {
  return items.map((item) => ({ sku: item.sku, qty: item.qty, gift_sku: item.gift_sku ?? null }));
}

/** Расчёт корзины на сервере: цены, наличие, подарки. Пересчитывается при каждом изменении корзины. */
export function useQuote(items: CartItem[]): { quote?: Quote; error?: string; loading: boolean } {
  const key = JSON.stringify(toRequestItems(items));
  const [state, setState] = useState<State | null>(null);

  useEffect(() => {
    const requestItems: CartRequestItem[] = JSON.parse(key);
    if (requestItems.length === 0) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetchQuote(requestItems, controller.signal)
        .then((quote) => setState({ key, quote }))
        .catch((error: Error) => {
          if (error.name !== "AbortError") setState({ key, error: error.message });
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [key]);

  const current = state?.key === key ? state : null;
  return { quote: current?.quote, error: current?.error, loading: items.length > 0 && current === null };
}
