import { getDictionary, type Locale } from "@/lib/i18n";

import styles from "./SiteFooter.module.css";

export function SiteFooter({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.row}`}>
        <span className={styles.logo}>Sovgʻa</span>
        <span>{dict.freeDelivery}</span>
        <span className={styles.muted}>{dict.heroText}</span>
      </div>
    </footer>
  );
}
