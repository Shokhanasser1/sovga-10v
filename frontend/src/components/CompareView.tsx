"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchComparison } from "@/lib/api-client";
import { removeFromCompare } from "@/lib/compare-store";
import { formatValue } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import type { ComparisonRow } from "@/lib/schemas";
import { useCompare } from "@/lib/use-compare";

import styles from "./CompareView.module.css";

type Result = { key: string; rows?: ComparisonRow[]; error?: string };

export function CompareView({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  const items = useCompare();
  const key = items.map((item) => item.sku).join(",");
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    const skus = key.split(",").filter(Boolean);
    if (skus.length < 2) return;
    let cancelled = false;
    fetchComparison(skus, lang)
      .then((rows) => !cancelled && setResult({ key, rows }))
      .catch((error: Error) => !cancelled && setResult({ key, error: error.message }));
    return () => {
      cancelled = true;
    };
  }, [key, lang]);

  const current = result?.key === key ? result : null;

  return (
    <div className="container">
      <h1 className={`display ${styles.title}`}>{dict.compareTitle}</h1>
      {items.length < 2 && <p className="notice">{dict.compareEmpty}</p>}
      {current?.error && (
        <p className="notice" role="alert">
          {current.error}
        </p>
      )}
      {items.length > 0 && (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <td />
                {items.map((item) => (
                  <th key={item.sku} scope="col" className={styles.head}>
                    <Link href={`/${lang}/product/${item.slug}`} className={styles.model}>
                      {localized(item, lang)}
                    </Link>
                    <span className={styles.variant}>{item.variantLabel}</span>
                    <button type="button" className={styles.remove} onClick={() => removeFromCompare(item.sku)}>
                      {dict.compareRemove}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {current?.rows?.map((row) => (
                <tr key={row.code}>
                  <th scope="row" className={styles.rowName}>
                    {row.name}
                  </th>
                  {row.values.map((value, index) => {
                    const best = row.best.includes(index);
                    return (
                      <td key={index} className={best ? styles.best : undefined}>
                        {value === null ? "—" : formatValue(value, row.unit, lang)}
                        {best && <span className="visually-hidden"> — {dict.compareBest}</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
