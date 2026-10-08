import { notFound } from "next/navigation";
import { Suspense } from "react";

import { OrderView } from "@/components/OrderView";
import { isLocale } from "@/lib/i18n";

async function OrderContent({ params }: Pick<PageProps<"/[lang]/orders/[number]">, "params">) {
  const { lang, number } = await params;
  if (!isLocale(lang)) notFound();
  return <OrderView lang={lang} number={number} />;
}

export default function OrderPage({ params }: PageProps<"/[lang]/orders/[number]">) {
  return (
    <Suspense fallback={<div className="container" style={{ minHeight: "50vh" }} />}>
      <OrderContent params={params} />
    </Suspense>
  );
}
