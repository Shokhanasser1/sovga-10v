import { notFound } from "next/navigation";

import { CompareView } from "@/components/CompareView";
import { isLocale } from "@/lib/i18n";

export default async function ComparePage({ params }: PageProps<"/[lang]/compare">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  return <CompareView lang={lang} />;
}
