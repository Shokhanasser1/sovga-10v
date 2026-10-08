import { notFound } from "next/navigation";

import { OrdersView } from "@/components/OrdersView";
import { isLocale } from "@/lib/i18n";

export default async function OrdersPage({ params }: PageProps<"/[lang]/orders">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  return <OrdersView lang={lang} />;
}
