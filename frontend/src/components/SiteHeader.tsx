import Link from "next/link";
import { Suspense } from "react";

import { LOCALES, getDictionary, type Locale } from "@/lib/i18n";

import { CartLink } from "./CartLink";
import { CompareLink } from "./CompareLink";
import { LangSwitch } from "./LangSwitch";
import { SearchBox } from "./SearchBox";
import styles from "./SiteHeader.module.css";

export function SiteHeader({ lang }: { lang: Locale }) {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.row}`}>
        <Link href={`/${lang}`} className={styles.logo} aria-label="Sovgʻa">
          Sov<span className={styles.mark}>gʻ</span>a
        </Link>
        <div className={styles.search}>
          <SearchBox lang={lang} />
        </div>
        <nav className={styles.nav}>
          <CartLink lang={lang} />
          <CompareLink lang={lang} />
          <Link href={`/${lang}/orders`} className={styles.account}>
            {getDictionary(lang).ordersShort}
          </Link>
        </nav>
        <div className={styles.lang}>
          {/* Адрес страницы известен только во время запроса — до этого простые ссылки на главные. */}
          <Suspense fallback={<LangSwitch lang={lang} hrefs={Object.fromEntries(LOCALES.map((l) => [l, `/${l}`]))} />}>
            <LangSwitch lang={lang} />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
