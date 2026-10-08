import { NextResponse, type NextRequest } from "next/server";

import { DEFAULT_LOCALE, isLocale, type Locale } from "@/lib/i18n";

function preferredLocale(request: NextRequest): Locale {
  const accepted = request.headers.get("accept-language")?.toLowerCase() ?? "";
  return accepted.startsWith("uz") ? "uz" : DEFAULT_LOCALE;
}

/** Адрес без языка (/, /catalog/x, /en) → тот же путь на языке посетителя. */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (isLocale(pathname.split("/")[1] ?? "")) return;
  const url = request.nextUrl.clone();
  url.pathname = `/${preferredLocale(request)}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Не трогаем API, служебные файлы Next.js и всё с расширением (картинки, favicon).
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
