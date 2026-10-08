import "../globals.css";

import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { LOCALES, isLocale } from "@/lib/i18n";

import { fontClasses } from "../fonts";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: { default: "Sovgʻa — смартфоны с подарком", template: "%s — Sovgʻa" },
  description: "Смартфоны, планшеты и аксессуары в Узбекистане. Подарок к каждому смартфону, доставка бесплатно.",
};

export function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}

export default async function LangLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  return (
    <html lang={lang} className={fontClasses}>
      <body>
        <SiteHeader lang={lang} />
        <main>{children}</main>
        <SiteFooter lang={lang} />
      </body>
    </html>
  );
}
