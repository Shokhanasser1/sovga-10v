import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DeviceArt, kindFor } from "@/components/DeviceArt";
import { IkatRibbon } from "@/components/IkatRibbon";
import { ProductGrid } from "@/components/ProductGrid";
import { getCategories, getProducts } from "@/lib/api";
import { getDictionary, isLocale, localized, type Locale } from "@/lib/i18n";

import styles from "./home.module.css";

const FEATURED = 8;

async function Categories({ lang }: { lang: Locale }) {
  const categories = (await getCategories()).filter((category) => category.parent === null);
  return (
    <ul className={styles.categories}>
      {categories.map((category) => (
        <li key={category.slug}>
          <Link href={`/${lang}/catalog/${category.slug}`} className={styles.category}>
            <DeviceArt kind={kindFor(category.slug)} className={styles.categoryArt} />
            <span>{localized(category, lang)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

async function Available({ lang }: { lang: Locale }) {
  const page = await getProducts({ available: "1", sort: "price_desc" });
  return <ProductGrid products={(page?.results ?? []).slice(0, FEATURED)} lang={lang} />;
}

export default async function HomePage({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  const dict = getDictionary(lang);
  return (
    <>
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <h1 className={`display ${styles.title}`}>{dict.heroTitle}</h1>
            <p className={styles.lead}>{dict.heroText}</p>
            <a className="button" href="#catalog">
              {dict.toCatalog}
            </a>
          </div>
        </div>
        <IkatRibbon className={styles.ribbonVertical} length={640} />
        <IkatRibbon className={styles.ribbonHorizontal} orientation="horizontal" length={1600} />
        <p className={styles.tag}>
          <span className={styles.tagHole} aria-hidden="true" />
          {dict.heroGiftTag}
        </p>
      </section>

      <section id="catalog" className={`container ${styles.section}`}>
        <h2 className={`display ${styles.sectionTitle}`}>{dict.categoriesTitle}</h2>
        <Suspense fallback={<div className={styles.placeholder} />}>
          <Categories lang={lang} />
        </Suspense>
      </section>

      <section className={`container ${styles.section}`}>
        <h2 className={`display ${styles.sectionTitle}`}>{dict.availableTitle}</h2>
        <Suspense fallback={<div className={styles.placeholder} />}>
          <Available lang={lang} />
        </Suspense>
      </section>
    </>
  );
}
