"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { LOCALES, switchLocalePath, type Locale } from "@/lib/i18n";

import styles from "./LangSwitch.module.css";

function CurrentPathSwitch({ lang }: { lang: Locale }) {
  const pathname = usePathname();
  const hrefs = Object.fromEntries(LOCALES.map((locale) => [locale, switchLocalePath(pathname, locale)]));
  return <Links lang={lang} hrefs={hrefs} />;
}

export function LangSwitch({ lang, hrefs }: { lang: Locale; hrefs?: Record<string, string> }) {
  return hrefs ? <Links lang={lang} hrefs={hrefs} /> : <CurrentPathSwitch lang={lang} />;
}

function Links({ lang, hrefs }: { lang: Locale; hrefs: Record<string, string> }) {
  return (
    <div className={styles.switch} role="group" aria-label="Язык / Til">
      {LOCALES.map((locale) => (
        <Link
          key={locale}
          href={hrefs[locale]}
          hrefLang={locale}
          aria-current={locale === lang ? "true" : undefined}
          className={locale === lang ? styles.active : styles.option}
        >
          {locale.toUpperCase()}
        </Link>
      ))}
    </div>
  );
}
