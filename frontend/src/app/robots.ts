import type { MetadataRoute } from "next";

const SITE_URL = process.env.SITE_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Поиск и сравнение — бесконечные сочетания параметров, индексировать их незачем.
      disallow: ["/api/", "/ru/search", "/uz/search", "/ru/compare", "/uz/compare"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
