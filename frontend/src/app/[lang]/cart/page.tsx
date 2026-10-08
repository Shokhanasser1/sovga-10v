import { notFound } from "next/navigation";

import { CartView } from "@/components/CartView";
import { isLocale } from "@/lib/i18n";

export default async function CartPage({ params }: PageProps<"/[lang]/cart">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  return <CartView lang={lang} />;
}
