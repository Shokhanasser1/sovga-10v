"use client";

import { useMemo, useSyncExternalStore } from "react";

import { COMPARE_KEY, parseCompare, subscribeCompare, type CompareItem } from "./compare-store";

function snapshot(): string {
  try {
    return window.localStorage.getItem(COMPARE_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Текущий список сравнения; обновляется при изменении в этой и других вкладках. */
export function useCompare(): CompareItem[] {
  const raw = useSyncExternalStore(subscribeCompare, snapshot, () => "");
  return useMemo(() => parseCompare(raw), [raw]);
}
