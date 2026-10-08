import Link from "next/link";

import { formatPriceFrom } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import type { ProductSummary } from "@/lib/schemas";

import { DeviceArt, kindFor } from "./DeviceArt";
import styles from "./ProductCard.module.css";

export function ProductCard({ product, lang }: { product: ProductSummary; lang: Locale }) {
  const dict = getDictionary(lang);
  return (
    <Link href={`/${lang}/product/${product.slug}`} className={styles.card}>
      <div className={styles.art}>
        <DeviceArt kind={kindFor(product.category)} label={product.brand.name} />
      </div>
      <div className={styles.body}>
        <span className={styles.brand}>{product.brand.name}</span>
        <span className={styles.name}>{localized(product, lang)}</span>
        <span className={`price ${styles.price}`}>
          {product.price_from_uzs ? formatPriceFrom(product.price_from_uzs, lang) : dict.noPrice}
        </span>
        <span className={product.is_available ? styles.available : styles.unavailable}>
          {product.is_available ? dict.onSale : dict.outOfStock}
        </span>
      </div>
    </Link>
  );
}
