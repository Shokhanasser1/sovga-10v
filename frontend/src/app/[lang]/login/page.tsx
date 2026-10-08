import { notFound } from "next/navigation";
import { Suspense } from "react";

import { LoginView } from "@/components/LoginView";
import { isLocale } from "@/lib/i18n";

export default async function LoginPage({ params }: PageProps<"/[lang]/login">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  // Адрес возврата (?next=) читается в браузере — до этого показываем пустой каркас.
  return (
    <Suspense fallback={<div className="container" style={{ minHeight: "50vh" }} />}>
      <LoginView lang={lang} />
    </Suspense>
  );
}
