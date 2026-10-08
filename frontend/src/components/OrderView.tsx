"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiClientError, cancelOrder, fetchOrder } from "@/lib/api-client";
import { formatSum } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import { formatDateTime } from "@/lib/navigation";
import type { Order } from "@/lib/schemas";

import forms from "./Forms.module.css";
import styles from "./OrderView.module.css";

export function OrderView({ lang, number }: { lang: Locale; number: string }) {
  const dict = getDictionary(lang);
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchOrder(number)
      .then(setOrder)
      .catch((failure: ApiClientError) => {
        if (failure.status === 403) {
          router.replace(`/${lang}/login?next=${encodeURIComponent(`/${lang}/orders/${number}`)}`);
        } else {
          setError(failure.status === 404 ? dict.notFoundTitle : failure.message);
        }
      });
  }, [number, lang, router, dict.notFoundTitle]);

  async function cancel() {
    setBusy(true);
    try {
      setOrder(await cancelOrder(number));
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !order) return <div className={`container ${forms.page}`}><p className="notice">{error}</p></div>;
  if (!order) return <div className={`container ${forms.page}`} style={{ minHeight: "50vh" }} />;

  return (
    <div className={`container ${forms.wide}`}>
      <h1 className={`display ${forms.title}`}>{dict.orderTitle(order.number)}</h1>
      <p className={styles.status} data-status={order.status}>
        {dict.orderStatus[order.status]}
      </p>
      {error && (
        <p className={forms.error} role="alert">
          {error}
        </p>
      )}
      {order.status === "confirmed" && (
        <div className={styles.notice}>
          <p>{dict.priceLocked(formatDateTime(order.price_lock_until, lang))}</p>
          <p>{dict.payNext}</p>
        </div>
      )}
      <div className={forms.checkout}>
        <section className={forms.card}>
          {order.lines.map((line) => (
            <div key={`${line.sku}-${line.is_gift}`} className={forms.summaryLine}>
              <span>
                <Link href={`/${lang}/product/${line.slug}`}>{localized(line, lang)}</Link> × {line.qty}
                {line.is_gift && <span className={styles.giftBadge}>{dict.giftLabel}</span>}
              </span>
              <span className="price">{line.is_gift ? "0" : formatSum(line.price_uzs * line.qty, lang)}</span>
            </div>
          ))}
          <p className={forms.total}>
            <span>{dict.total}</span>
            <span className="price">{formatSum(order.total_uzs, lang)}</span>
          </p>
          <p className={forms.hint}>
            {order.address_text}
            {order.address_landmark && ` — ${order.address_landmark}`}
          </p>
          {order.can_cancel && (
            <button className="button button-ghost" type="button" style={{ marginTop: 16 }} disabled={busy} onClick={cancel}>
              {dict.cancelOrder}
            </button>
          )}
        </section>
        <ol className={`${forms.card} ${styles.timeline}`}>
          {order.events.map((event) => (
            <li key={`${event.status}-${event.at}`}>
              <strong>{dict.orderStatus[event.status]}</strong>
              <span>{formatDateTime(event.at, lang)}</span>
              {event.note && <span>{event.note}</span>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
