"use client";

import { useEffect, useState } from "react";

import { fetchDemo } from "@/lib/api-client";
import { getDictionary, type Locale } from "@/lib/i18n";

import styles from "./DemoBanner.module.css";

/** Учебный режим: всем видно, что оплата, коды входа и Telegram — имитация. */
export function DemoBanner({ lang }: { lang: Locale }) {
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    fetchDemo()
      .then(setDemo)
      .catch(() => setDemo(false));
  }, []);

  if (!demo) return null;
  return (
    <p className={styles.banner}>
      {getDictionary(lang).demoBanner}
    </p>
  );
}
