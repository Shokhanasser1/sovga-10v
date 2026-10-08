import { NextResponse, type NextRequest } from "next/server";

import { DEFAULT_LOCALE, isLocale, type Locale } from "@/lib/i18n";

// Заголовки, которыми клиент мог бы выдать себя за другого посетителя перед лимитом запросов Django.
const SPOOFABLE = ["x-real-ip", "x-forwarded-for", "x-internal-token"];

function preferredLocale(request: NextRequest): Locale {
  const accepted = request.headers.get("accept-language")?.toLowerCase() ?? "";
  return accepted.startsWith("uz") ? "uz" : DEFAULT_LOCALE;
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/api/")) {
    const headers = new Headers(request.headers);
    for (const name of SPOOFABLE) headers.delete(name);
    return NextResponse.next({ request: { headers } });
  }

  // Адрес без языка (/, /catalog/x, /en) → тот же путь на языке посетителя.
  if (isLocale(pathname.split("/")[1] ?? "")) return;
  const url = request.nextUrl.clone();
  url.pathname = `/${preferredLocale(request)}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Служебные файлы Next.js и всё с расширением (картинки, favicon, sitemap.xml) не трогаем.
  matcher: ["/((?!_next|.*\\..*).*)"],
};
