/**
 * Корзина в localStorage до оформления заказа — работает и без входа,
 * после входа остаётся той же самой. До 10 позиций, до 5 штук каждой.
 */

import { z } from "zod";

import { browserStorage, createLocalList, type Storage } from "./local-store";

export const MAX_QTY = 5;

const cartItemSchema = z.object({
  sku: z.string().min(1).max(64),
  slug: z.string().max(200),
  name_ru: z.string().max(200),
  name_uz: z.string().max(200),
  variantLabel: z.string().max(200),
  qty: z.number().int().min(1).max(MAX_QTY),
  // undefined — подарок подберётся сам; null — покупатель отказался от подарка.
  gift_sku: z.string().max(64).nullable().optional(),
});

export type CartItem = z.infer<typeof cartItemSchema>;

export const cartList = createLocalList("sovga:cart:v1", cartItemSchema, 10);
export const parseCart = cartList.parse;
export const subscribeCart = cartList.subscribe;

export function readCart(store: Storage | null = browserStorage()): CartItem[] {
  return cartList.read(store);
}

/** Добавить товар; уже лежащий — увеличить количество. Возвращает false, если места нет. */
export function addToCart(item: Omit<CartItem, "qty">, store: Storage | null = browserStorage()): boolean {
  const items = readCart(store);
  const existing = items.find((line) => line.sku === item.sku);
  if (existing) {
    cartList.write(
      items.map((line) => (line.sku === item.sku ? { ...line, qty: Math.min(MAX_QTY, line.qty + 1) } : line)),
      store,
    );
    return true;
  }
  if (items.length >= cartList.limit) return false;
  cartList.write([...items, { ...item, qty: 1 }], store);
  return true;
}

export function setCartQty(sku: string, qty: number, store: Storage | null = browserStorage()): CartItem[] {
  const clamped = Math.max(1, Math.min(MAX_QTY, Math.round(qty)));
  return cartList.write(readCart(store).map((line) => (line.sku === sku ? { ...line, qty: clamped } : line)), store);
}

export function setCartGift(sku: string, giftSku: string | null, store: Storage | null = browserStorage()): CartItem[] {
  return cartList.write(readCart(store).map((line) => (line.sku === sku ? { ...line, gift_sku: giftSku } : line)), store);
}

export function removeFromCart(sku: string, store: Storage | null = browserStorage()): CartItem[] {
  return cartList.write(readCart(store).filter((line) => line.sku !== sku), store);
}

export function clearCart(store: Storage | null = browserStorage()): void {
  cartList.write([], store);
}
