import type { MetadataRoute } from "next";

const SITE_URL = process.env.SITE_URL ?? "http://localhost:3000";
// Бесконечные сочетания параметров и личные страницы покупателя индексировать незачем.
const PRIVATE = ["search", "compare", "cart", "checkout", "orders", "login"];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", ...PRIVATE.flatMap((path) => [`/ru/${path}`, `/uz/${path}`])],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
