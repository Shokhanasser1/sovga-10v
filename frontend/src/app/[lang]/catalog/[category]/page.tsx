import { notFound } from "next/navigation";
import { Suspense } from "react";

import { CatalogView } from "@/components/CatalogView";
import { getCategories } from "@/lib/api";
import { isLocale, localized } from "@/lib/i18n";

async function CategoryCatalog({
  params,
  searchParams,
}: Pick<PageProps<"/[lang]/catalog/[category]">, "params" | "searchParams">) {
  const { lang, category: slug } = await params;
  if (!isLocale(lang)) notFound();
  const category = (await getCategories()).find((item) => item.slug === slug);
  if (!category) notFound();
  return (
    <CatalogView
      lang={lang}
      path={`/${lang}/catalog/${slug}`}
      title={localized(category, lang)}
      category={slug}
      searchParams={await searchParams}
    />
  );
}

export default function CategoryPage({ params, searchParams }: PageProps<"/[lang]/catalog/[category]">) {
  return (
    <Suspense fallback={<div className="container" style={{ minHeight: "60vh" }} />}>
      <CategoryCatalog params={params} searchParams={searchParams} />
    </Suspense>
  );
}
