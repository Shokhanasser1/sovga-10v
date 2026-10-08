import type { Locale } from "./i18n";

/** Куда вернуться после входа: только пути этого сайта на том же языке — без открытых перенаправлений. */
export function safeNext(next: string | null | undefined, lang: Locale): string {
  const fallback = `/${lang}/orders`;
  if (!next || !next.startsWith(`/${lang}/`) || next.startsWith("//") || /[\\\s]/.test(next)) return fallback;
  return next;
}

export function formatDateTime(iso: string, lang: Locale): string {
  return new Intl.DateTimeFormat(lang === "uz" ? "uz-UZ" : "ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Tashkent",
  }).format(new Date(iso));
}
