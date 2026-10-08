"use client";

import Link from "next/link";

import { getDictionary, type Locale } from "@/lib/i18n";
import { useCompare } from "@/lib/use-compare";

import styles from "./CompareLink.module.css";

export function CompareLink({ lang }: { lang: Locale }) {
  const count = useCompare().length;
  return (
    <Link href={`/${lang}/compare`} className={styles.link}>
      {getDictionary(lang).compare}
      {count > 0 && <span className={styles.count}>{count}</span>}
    </Link>
  );
}
