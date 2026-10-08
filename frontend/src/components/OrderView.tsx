"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiClientError, cancelOrder, fetchOrder, payLink, telegramLink } from "@/lib/api-client";
import { formatSum, withVariant } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import { formatDate, formatDateTime } from "@/lib/navigation";
import type { Order } from "@/lib/schemas";

import forms from "./Forms.module.css";
import styles from "./OrderView.module.css";

const PROVIDER_NAMES = { payme: "Payme", click: "Click" } as const;

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

  async function pay(provider: "payme" | "click") {
    setBusy(true);
    setError("");
    try {
      window.location.assign(await payLink(number, provider, lang));
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }

  async function connectTelegram() {
    setBusy(true);
    setError("");
    try {
      const url = await telegramLink(lang);
      // Новая вкладка, чтобы страница заказа осталась; если браузер её заблокировал — переходим в этой.
      const tab = window.open(url, "_blank");
      if (tab) tab.opener = null;
      else window.location.assign(url);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

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
      {order.can_pay && (
        <div className={styles.notice}>
          <p>{dict.priceLocked(formatDateTime(order.price_lock_until, lang))}</p>
          {order.pay_providers.length > 0 ? (
            <div className={styles.payButtons}>
              {order.pay_providers.map((provider) => (
                <button key={provider} className="button" type="button" disabled={busy} onClick={() => pay(provider)}>
                  {busy ? dict.payRedirect : dict.payWith(PROVIDER_NAMES[provider])}
                </button>
              ))}
            </div>
          ) : (
            <p>{dict.payNext}</p>
          )}
        </div>
      )}
      <div className={forms.checkout}>
        <section className={forms.card}>
          {order.lines.map((line) => (
            <div key={`${line.sku}-${line.is_gift}`} className={forms.summaryLine}>
              <span>
                <Link href={`/${lang}/product/${line.slug}`}>{withVariant(localized(line, lang), line.axes, lang)}</Link> ×{" "}
                {line.qty}
                {line.is_gift && <span className={styles.giftBadge}>{dict.giftLabel}</span>}
                {line.devices.map((device) => (
                  <span key={device.imei} className={styles.device}>
                    {dict.warranty(device.imei, formatDate(device.warranty_until, lang))}
                  </span>
                ))}
              </span>
              <span className="price">{line.is_gift ? dict.free : formatSum(line.price_uzs * line.qty, lang)}</span>
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
          {order.shipment && (
            <p className={styles.delivery}>
              {order.shipment.carrier === "own" ? (
                <>
                  {dict.deliveryCourier(order.shipment.courier_name)},{" "}
                  <a href={`tel:${order.shipment.courier_phone}`}>{order.shipment.courier_phone}</a>
                </>
              ) : (
                dict.deliveryService(order.shipment.service_name, order.shipment.tracking)
              )}
            </p>
          )}
          {order.telegram === "linked" && <p className={forms.hint}>{dict.telegramLinked}</p>}
          <div className={styles.actions}>
            {order.telegram === "available" && (
              <button className="button button-ghost" type="button" disabled={busy} onClick={connectTelegram}>
                {dict.telegramConnect}
              </button>
            )}
            {order.can_cancel && (
              <button className="button button-ghost" type="button" disabled={busy} onClick={cancel}>
                {dict.cancelOrder}
              </button>
            )}
          </div>
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
