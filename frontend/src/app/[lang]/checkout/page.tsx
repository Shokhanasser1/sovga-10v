import { notFound } from "next/navigation";

import { CheckoutView } from "@/components/CheckoutView";
import { isLocale } from "@/lib/i18n";

export default async function CheckoutPage({ params }: PageProps<"/[lang]/checkout">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  return <CheckoutView lang={lang} />;
}
