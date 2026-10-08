"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiClientError, fetchOrders, logout } from "@/lib/api-client";
import { formatSum } from "@/lib/format";
import { getDictionary, type Locale } from "@/lib/i18n";
import { formatDateTime } from "@/lib/navigation";
import type { Order } from "@/lib/schemas";

import forms from "./Forms.module.css";

export function OrdersView({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  const router = useRouter();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchOrders()
      .then(setOrders)
      .catch((failure: ApiClientError) => {
        if (failure.status === 403) router.replace(`/${lang}/login?next=${encodeURIComponent(`/${lang}/orders`)}`);
        else setError(failure.message);
      });
  }, [lang, router]);

  async function signOut() {
    await logout();
    router.replace(`/${lang}`);
    router.refresh();
  }

  return (
    <div className={`container ${forms.page}`}>
      <h1 className={`display ${forms.title}`}>{dict.account}</h1>
      {error && <p className={forms.error}>{error}</p>}
      {orders?.length === 0 && <p className="notice">{dict.ordersEmpty}</p>}
      {orders?.map((order) => (
        <Link key={order.number} href={`/${lang}/orders/${order.number}`} className={forms.card}
          style={{ display: "block", marginBottom: 12, textDecoration: "none" }}>
          <strong>{dict.orderTitle(order.number)}</strong> — {dict.orderStatus[order.status]}
          <p className={forms.hint}>
            {formatDateTime(order.created_at, lang)} · <span className="price">{formatSum(order.total_uzs, lang)}</span>
          </p>
        </Link>
      ))}
      {orders && (
        <button className={forms.link} type="button" onClick={signOut}>
          {dict.logout}
        </button>
      )}
    </div>
  );
}
