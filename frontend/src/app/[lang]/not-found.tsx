import Link from "next/link";

import { getDictionary } from "@/lib/i18n";

// not-found не получает params, поэтому текст на обоих языках.
export default function NotFound() {
  const ru = getDictionary("ru");
  const uz = getDictionary("uz");
  return (
    <div className="container" style={{ padding: "64px var(--gutter)" }}>
      <h1 className="display">{ru.notFoundTitle}</h1>
      <p>{ru.notFoundText}</p>
      <p lang="uz">
        {uz.notFoundTitle}. {uz.notFoundText}
      </p>
      <Link className="button" href="/ru">
        {ru.catalog}
      </Link>
    </div>
  );
}
