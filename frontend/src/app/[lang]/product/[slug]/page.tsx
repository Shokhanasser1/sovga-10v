import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ProductGrid } from "@/components/ProductGrid";
import { ProductPurchase } from "@/components/ProductPurchase";
import { getAccessories, getProduct } from "@/lib/api";
import { getDictionary, isLocale } from "@/lib/i18n";

import styles from "./product.module.css";

async function ProductContent({ params }: Pick<PageProps<"/[lang]/product/[slug]">, "params">) {
  const { lang, slug } = await params;
  if (!isLocale(lang)) notFound();
  const [product, accessories] = await Promise.all([getProduct(slug), getAccessories(slug)]);
  if (!product) notFound();
  const dict = getDictionary(lang);
  return (
    <>
      <nav className={styles.crumbs} aria-label={dict.catalog}>
        <Link href={`/${lang}/catalog/${product.category}`}>← {dict.catalog}</Link>
      </nav>
      <ProductPurchase product={product} lang={lang} />
      {accessories.length > 0 && (
        <section className={styles.section}>
          <h2 className={`display ${styles.title}`}>{dict.accessories}</h2>
          <ProductGrid products={accessories} lang={lang} />
        </section>
      )}
    </>
  );
}

export default function ProductPage({ params }: PageProps<"/[lang]/product/[slug]">) {
  return (
    <div className={`container ${styles.page}`}>
      <Suspense fallback={<div style={{ minHeight: "70vh" }} />}>
        <ProductContent params={params} />
      </Suspense>
    </div>
  );
}
