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

/** Дата без времени («2027-10-08»): форматируем как есть, без сдвига часового пояса. */
export function formatDate(isoDate: string, lang: Locale): string {
  return new Intl.DateTimeFormat(lang === "uz" ? "uz-UZ" : "ru-RU", { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(`${isoDate}T00:00:00Z`),
  );
}
