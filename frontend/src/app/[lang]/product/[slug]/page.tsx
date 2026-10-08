import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ProductGrid } from "@/components/ProductGrid";
import { ProductJsonLd } from "@/components/ProductJsonLd";
import { ProductPurchase } from "@/components/ProductPurchase";
import { getAccessories, getOffers, getProduct } from "@/lib/api";
import { LOCALES, getDictionary, isLocale, localized } from "@/lib/i18n";

import styles from "./product.module.css";

export async function generateMetadata({ params }: PageProps<"/[lang]/product/[slug]">): Promise<Metadata> {
  const { lang, slug } = await params;
  if (!isLocale(lang)) return {};
  const product = await getProduct(slug);
  if (!product) return {};
  const name = localized(product, lang);
  const seoTitle = lang === "uz" ? product.seo_title_uz : product.seo_title_ru;
  const seoDescription = lang === "uz" ? product.seo_description_uz : product.seo_description_ru;
  return {
    title: seoTitle || name,
    description: seoDescription || getDictionary(lang).productDescription(name),
    alternates: {
      canonical: `/${lang}/product/${slug}`,
      languages: Object.fromEntries(LOCALES.map((locale) => [locale, `/${locale}/product/${slug}`])),
    },
  };
}

async function ProductContent({ params }: Pick<PageProps<"/[lang]/product/[slug]">, "params">) {
  const { lang, slug } = await params;
  if (!isLocale(lang)) notFound();
  const [product, accessories, offers] = await Promise.all([
    getProduct(slug),
    getAccessories(slug),
    getOffers(slug),
  ]);
  if (!product) notFound();
  const dict = getDictionary(lang);
  return (
    <>
      <ProductJsonLd product={product} offers={offers} lang={lang} />
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
