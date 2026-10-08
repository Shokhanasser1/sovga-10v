"use client";

import Link from "next/link";

import { getDictionary, type Locale } from "@/lib/i18n";
import { useCart } from "@/lib/use-compare";

import styles from "./CompareLink.module.css";

export function CartLink({ lang }: { lang: Locale }) {
  const count = useCart().reduce((sum, item) => sum + item.qty, 0);
  return (
    <Link href={`/${lang}/cart`} className={styles.link}>
      {getDictionary(lang).cart}
      {count > 0 && <span className={styles.count}>{count}</span>}
    </Link>
  );
}
