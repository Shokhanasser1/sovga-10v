import "./globals.css";

import type { Metadata } from "next";
import Link from "next/link";

import { fontClasses } from "./fonts";

export const metadata: Metadata = { title: "404 — Sovgʻa" };

export default function GlobalNotFound() {
  return (
    <html lang="ru" className={fontClasses}>
      <body>
        <main className="container" style={{ padding: "80px var(--gutter)" }}>
          <h1 className="display">Такой страницы нет</h1>
          <p>Bunday sahifa yoʻq.</p>
          <p>
            <Link className="button" href="/ru">
              На главную
            </Link>
          </p>
        </main>
      </body>
    </html>
  );
}
