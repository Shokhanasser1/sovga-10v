import { notFound } from "next/navigation";
import { Suspense } from "react";

import { CatalogView } from "@/components/CatalogView";
import { getDictionary, isLocale } from "@/lib/i18n";

async function SearchResults({ params, searchParams }: Pick<PageProps<"/[lang]/search">, "params" | "searchParams">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  const query = await searchParams;
  const text = (Array.isArray(query.q) ? query.q[0] : query.q)?.trim() ?? "";
  const dict = getDictionary(lang);
  return (
    <CatalogView
      lang={lang}
      path={`/${lang}/search`}
      title={text ? dict.searchResults(text) : dict.catalog}
      searchParams={query}
    />
  );
}

export default function SearchPage({ params, searchParams }: PageProps<"/[lang]/search">) {
  return (
    <Suspense fallback={<div className="container" style={{ minHeight: "60vh" }} />}>
      <SearchResults params={params} searchParams={searchParams} />
    </Suspense>
  );
}
