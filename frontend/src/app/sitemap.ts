import type { MetadataRoute } from "next";
import { connection } from "next/server";

import { getSitemap } from "@/lib/api";
import { LOCALES } from "@/lib/i18n";

const SITE_URL = process.env.SITE_URL ?? "http://localhost:3000";

function entry(path: string): MetadataRoute.Sitemap[number] {
  const languages = Object.fromEntries(LOCALES.map((locale) => [locale, `${SITE_URL}/${locale}${path}`]));
  return { url: languages.ru, alternates: { languages } };
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Список товаров берём при запросе, а не при сборке: сборке не нужен работающий Django.
  await connection();
  const paths = [""];
  try {
    const { categories, products } = await getSitemap();
    paths.push(...categories.map((slug) => `/catalog/${slug}`), ...products.map((slug) => `/product/${slug}`));
  } catch {
    // Django недоступен — отдаём хотя бы главные страницы.
  }
  return paths.map(entry);
}
