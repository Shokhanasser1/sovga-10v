import type { Locale } from "@/lib/i18n";
import type { ProductSummary } from "@/lib/schemas";

import { ProductCard } from "./ProductCard";
import styles from "./ProductGrid.module.css";

export function ProductGrid({ products, lang }: { products: ProductSummary[]; lang: Locale }) {
  return (
    <ul className={styles.grid}>
      {products.map((product) => (
        <li key={product.slug}>
          <ProductCard product={product} lang={lang} />
        </li>
      ))}
    </ul>
  );
}
