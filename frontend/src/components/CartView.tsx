"use client";

import Link from "next/link";
import { useEffect } from "react";

import { removeFromCart, setCartGift, setCartQty, MAX_QTY, type CartItem } from "@/lib/cart-store";
import { formatSum, withVariant } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import type { QuoteLine } from "@/lib/schemas";
import { useCart } from "@/lib/use-compare";
import { useQuote } from "@/lib/use-quote";

import styles from "./CartView.module.css";
import { IkatRibbon } from "./IkatRibbon";

function GiftPicker({ item, line, lang }: { item: CartItem; line: QuoteLine; lang: Locale }) {
  const dict = getDictionary(lang);
  const chosen = item.gift_sku ?? null;
  return (
    <fieldset className={styles.gift}>
      <IkatRibbon orientation="horizontal" length={900} className={styles.giftRibbon} />
      <legend className={styles.giftLegend}>{dict.giftChoose(formatSum(line.gift_budget_uzs, lang))}</legend>
      {line.gift_options.map((option) => (
        <label key={option.sku} className={styles.giftOption}>
          <input
            type="radio"
            name={`gift-${item.sku}`}
            checked={chosen === option.sku}
            onChange={() => setCartGift(item.sku, option.sku)}
          />
          <span>{withVariant(localized(option, lang), option.axes, lang)}</span>
          <span className={styles.giftPrice}>{formatSum(option.price_uzs, lang)}</span>
        </label>
      ))}
      <label className={styles.giftOption}>
        <input type="radio" name={`gift-${item.sku}`} checked={chosen === null} onChange={() => setCartGift(item.sku, null)} />
        <span>{dict.noGift}</span>
      </label>
    </fieldset>
  );
}

function CartLineView({ item, line, lang }: { item: CartItem; line?: QuoteLine; lang: Locale }) {
  const dict = getDictionary(lang);
  return (
    <li className={styles.line}>
      <div className={styles.lineHead}>
        <div>
          <Link href={`/${lang}/product/${item.slug}`} className={styles.name}>
            {localized(item, lang)}
          </Link>
          {item.variantLabel && <p className={styles.variant}>{item.variantLabel}</p>}
        </div>
        <p className="price">{line?.unit_price_uzs ? formatSum(line.line_total_uzs, lang) : "…"}</p>
      </div>
      <div className={styles.controls}>
        <div className={styles.stepper} role="group" aria-label={dict.qty}>
          <button type="button" aria-label={dict.less} disabled={item.qty <= 1} onClick={() => setCartQty(item.sku, item.qty - 1)}>
            −
          </button>
          <span aria-live="polite">{item.qty}</span>
          <button type="button" aria-label={dict.more} disabled={item.qty >= MAX_QTY} onClick={() => setCartQty(item.sku, item.qty + 1)}>
            +
          </button>
        </div>
        <button type="button" className={styles.remove} onClick={() => removeFromCart(item.sku)}>
          {dict.remove}
        </button>
      </div>
      {line?.errors.map((error) => (
        <p key={error} className={styles.error} role="alert">
          {error}
        </p>
      ))}
      {line && line.gift_options.length > 0 && <GiftPicker item={item} line={line} lang={lang} />}
    </li>
  );
}

export function CartView({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  const items = useCart();
  const { quote, error } = useQuote(items);

  // Подарок выбран заранее — самый ценный, пока покупатель сам не выбрал другой или «без подарка».
  useEffect(() => {
    for (const line of quote?.lines ?? []) {
      const item = items.find((candidate) => candidate.sku === line.sku);
      if (item && item.gift_sku === undefined && line.gift_options.length > 0) {
        setCartGift(item.sku, line.gift_options[0].sku);
      }
    }
  }, [quote, items]);

  if (items.length === 0) {
    return (
      <div className="container">
        <h1 className={`display ${styles.title}`}>{dict.cart}</h1>
        <p className="notice">
          {dict.cartEmpty} <Link href={`/${lang}`}>{dict.catalog}</Link>
        </p>
      </div>
    );
  }

  const canOrder = quote?.can_order ?? false;
  return (
    <div className={`container ${styles.layout}`}>
      <section>
        <h1 className={`display ${styles.title}`}>{dict.cart}</h1>
        <ul className={styles.lines}>
          {items.map((item) => (
            <CartLineView key={item.sku} item={item} line={quote?.lines.find((line) => line.sku === item.sku)} lang={lang} />
          ))}
        </ul>
      </section>
      <aside className={styles.summary}>
        <p className={styles.totalLabel}>{dict.total}</p>
        <p className={`price ${styles.total}`}>{quote ? formatSum(quote.total_uzs, lang) : "…"}</p>
        <p className={styles.delivery}>{dict.freeDelivery}</p>
        {[...(quote?.errors ?? []), ...(error ? [error] : [])].map((message) => (
          <p key={message} className={styles.error} role="alert">
            {message}
          </p>
        ))}
        {canOrder ? (
          <Link className="button" href={`/${lang}/checkout`}>
            {dict.toCheckout}
          </Link>
        ) : (
          <button className="button" type="button" disabled>
            {dict.toCheckout}
          </button>
        )}
      </aside>
    </div>
  );
}
