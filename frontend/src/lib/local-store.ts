/** Список в localStorage с проверкой схемой и уведомлением подписчиков (в этой и других вкладках). */

import { z } from "zod";

export type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;

export function browserStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function createLocalList<T>(key: string, item: z.ZodType<T>, limit: number) {
  const event = `${key}:change`;
  const schema = z.array(item);

  function parse(raw: string | null): T[] {
    if (!raw) return [];
    try {
      const parsed = schema.safeParse(JSON.parse(raw));
      return parsed.success ? parsed.data.slice(0, limit) : [];
    } catch {
      return [];
    }
  }

  function read(store: Storage | null = browserStorage()): T[] {
    if (!store) return [];
    try {
      return parse(store.getItem(key));
    } catch {
      return [];
    }
  }

  function write(items: T[], store: Storage | null = browserStorage()): T[] {
    if (store) {
      try {
        store.setItem(key, JSON.stringify(items));
      } catch {
        return items;
      }
    }
    if (typeof window !== "undefined") window.dispatchEvent(new Event(event));
    return items;
  }

  function snapshot(): string {
    try {
      return window.localStorage.getItem(key) ?? "";
    } catch {
      return "";
    }
  }

  function subscribe(callback: () => void): () => void {
    if (typeof window === "undefined") return () => {};
    const onStorage = (storageEvent: StorageEvent) => {
      if (storageEvent.key === key) callback();
    };
    window.addEventListener(event, callback);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(event, callback);
      window.removeEventListener("storage", onStorage);
    };
  }

  return { key, limit, parse, read, write, snapshot, subscribe };
}
