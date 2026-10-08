"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { createOrder, fetchMe } from "@/lib/api-client";
import { clearCart } from "@/lib/cart-store";
import { formatSum, withVariant } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import { useCart } from "@/lib/use-compare";
import { toRequestItems, useQuote } from "@/lib/use-quote";

import styles from "./Forms.module.css";

export function CheckoutView({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  const router = useRouter();
  const items = useCart();
  const { quote, error: quoteError } = useQuote(items);
  const [ready, setReady] = useState(false);
  const [address, setAddress] = useState("");
  const [landmark, setLandmark] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchMe()
      .then((customer) => {
        if (customer) {
          setReady(true);
          // Вернувшемуся покупателю — последний адрес; поля можно поправить.
          const saved = customer.address;
          if (saved) {
            setAddress((current) => current || saved.text);
            setLandmark((current) => current || saved.landmark);
          }
        } else router.replace(`/${lang}/login?next=${encodeURIComponent(`/${lang}/checkout`)}`);
      })
      .catch((failure: Error) => setError(failure.message));
  }, [lang, router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const order = await createOrder({ items: toRequestItems(items), address: { text: address, landmark }, comment });
      clearCart();
      router.push(`/${lang}/orders/${order.number}`);
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }

  if (items.length === 0) {
    return (
      <div className={`container ${styles.page}`}>
        <h1 className={`display ${styles.title}`}>{dict.checkout}</h1>
        <p className="notice">
          {dict.cartEmpty} <Link href={`/${lang}`}>{dict.catalog}</Link>
        </p>
      </div>
    );
  }

  const problem = error || quoteError || quote?.errors[0] || quote?.lines.flatMap((line) => line.errors)[0];
  return (
    <div className={`container ${styles.wide}`}>
      <h1 className={`display ${styles.title}`}>{dict.checkout}</h1>
      <form className={styles.checkout} onSubmit={submit}>
        <div className={styles.card}>
          {problem && (
            <p className={styles.error} role="alert">
              {problem}
            </p>
          )}
          <div className={styles.field}>
            <label htmlFor="address">{dict.address}</label>
            <input id="address" required minLength={5} maxLength={300} autoComplete="street-address" value={address}
              placeholder={dict.addressPlaceholder} onChange={(event) => setAddress(event.target.value)} />
          </div>
          <div className={styles.field}>
            <label htmlFor="landmark">{dict.landmark}</label>
            <input id="landmark" maxLength={200} value={landmark} placeholder={dict.landmarkPlaceholder}
              onChange={(event) => setLandmark(event.target.value)} />
          </div>
          <div className={styles.field}>
            <label htmlFor="comment">{dict.comment}</label>
            <textarea id="comment" maxLength={500} value={comment} placeholder={dict.commentPlaceholder}
              onChange={(event) => setComment(event.target.value)} />
          </div>
          <p className={styles.label}>{dict.payment}</p>
          <p className={styles.hint}>{dict.paymentCard}</p>
        </div>
        <aside className={styles.card}>
          {quote?.lines.map((line) => (
            <div key={line.sku}>
              <div className={styles.summaryLine}>
                <span>
                  {line.name_ru ? localized({ name_ru: line.name_ru, name_uz: line.name_uz ?? "" }, lang) : line.sku} ×{" "}
                  {line.qty}
                </span>
                <span className="price">{formatSum(line.line_total_uzs, lang)}</span>
              </div>
              {line.gift && (
                <p className={styles.summaryGift}>
                  + {dict.yourGift}: {withVariant(localized(line.gift, lang), line.gift.axes, lang)}
                </p>
              )}
            </div>
          ))}
          <p className={styles.total}>
            <span>{dict.total}</span>
            <span className="price">{quote ? formatSum(quote.total_uzs, lang) : "…"}</span>
          </p>
          <p className={styles.hint}>{dict.freeDelivery}</p>
          <button className="button" type="submit" style={{ width: "100%", marginTop: 16 }}
            disabled={!ready || busy || !quote?.can_order}>
            {busy ? dict.sending : dict.placeOrder}
          </button>
        </aside>
      </form>
    </div>
  );
}
