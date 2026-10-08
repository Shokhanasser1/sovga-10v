import Link from "next/link";

import { getFacets, getProducts } from "@/lib/api";
import { pageHref, toApiParams, type SearchParams } from "@/lib/catalog-params";
import { getDictionary, type Locale } from "@/lib/i18n";

import { AutoSubmitForm } from "./AutoSubmitForm";
import styles from "./CatalogView.module.css";
import { Filters } from "./Filters";
import { ProductGrid } from "./ProductGrid";

const PAGE_SIZE = 24;

export async function CatalogView({
  lang,
  path,
  title,
  category,
  searchParams,
}: {
  lang: Locale;
  path: string;
  title: string;
  category?: string;
  searchParams: SearchParams;
}) {
  const dict = getDictionary(lang);
  const params = toApiParams(searchParams, category);
  const [facets, page] = await Promise.all([
    getFacets({ category, q: params.q }),
    getProducts(params),
  ]);
  const products = page?.results ?? [];
  const current = Number(params.page ?? "1") || 1;
  const pages = Math.ceil((page?.count ?? 0) / PAGE_SIZE);
  const query = params.q ?? "";
  const resetHref = query ? `${path}?q=${encodeURIComponent(query)}` : path;

  return (
    <AutoSubmitForm action={path} className={`container ${styles.layout}`}>
      {query && <input type="hidden" name="q" value={query} />}
      <aside className={styles.aside}>
        {facets && <Filters facets={facets} searchParams={searchParams} lang={lang} resetHref={resetHref} />}
      </aside>
      <section className={styles.results}>
        <header className={styles.toolbar}>
          <div>
            <h1 className={`display ${styles.title}`}>{title}</h1>
            <p className={styles.count}>{dict.found(page?.count ?? 0)}</p>
          </div>
          <label className={styles.sort}>
            <span className="visually-hidden">{dict.sort}</span>
            <select name="sort" defaultValue={params.sort ?? (query ? "relevance" : "name")}>
              {query && <option value="relevance">{dict.sortRelevance}</option>}
              <option value="name">{dict.sortName}</option>
              <option value="price_asc">{dict.sortPriceAsc}</option>
              <option value="price_desc">{dict.sortPriceDesc}</option>
            </select>
          </label>
        </header>
        {products.length > 0 ? (
          <ProductGrid products={products} lang={lang} />
        ) : (
          <p className="notice">{query && !page?.count ? dict.searchNothing : dict.emptyCatalog}</p>
        )}
        {pages > 1 && (
          <nav className={styles.pagination} aria-label={dict.catalog}>
            {current > 1 && <Link href={pageHref(path, searchParams, current - 1)}>{dict.prev}</Link>}
            <span>
              {current} / {pages}
            </span>
            {current < pages && <Link href={pageHref(path, searchParams, current + 1)}>{dict.next}</Link>}
          </nav>
        )}
      </section>
    </AutoSubmitForm>
  );
}
