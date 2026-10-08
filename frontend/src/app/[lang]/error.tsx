"use client";

import { usePathname } from "next/navigation";

import { getDictionary, isLocale } from "@/lib/i18n";

export default function ErrorPage({ retry }: { error: Error; retry: () => void }) {
  const segment = usePathname().split("/")[1] ?? "";
  const dict = getDictionary(isLocale(segment) ? segment : "ru");
  return (
    <div className="container" style={{ padding: "64px var(--gutter)" }}>
      <p className="notice" role="alert">
        {dict.apiDown}
      </p>
      <button className="button" type="button" onClick={() => retry()}>
        {dict.retry}
      </button>
    </div>
  );
}
