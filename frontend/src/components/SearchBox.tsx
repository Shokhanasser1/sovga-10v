"use client";

import Form from "next/form";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState, type KeyboardEvent } from "react";

import { fetchSuggestions } from "@/lib/api-client";
import { formatPriceFrom } from "@/lib/format";
import { getDictionary, localized, type Locale } from "@/lib/i18n";
import type { Suggestions } from "@/lib/schemas";

import styles from "./SearchBox.module.css";

type Option = { href: string; label: string; meta: string };
const MIN_LENGTH = 2;

function toOptions(data: Suggestions, lang: Locale): Option[] {
  const dict = getDictionary(lang);
  return [
    ...data.categories.map((category) => ({
      href: `/${lang}/catalog/${category.slug}`,
      label: localized(category, lang),
      meta: dict.searchCategories,
    })),
    ...data.products.map((product) => ({
      href: `/${lang}/product/${product.slug}`,
      label: localized(product, lang),
      meta: product.price_from_uzs ? formatPriceFrom(product.price_from_uzs, lang) : product.brand.name,
    })),
  ];
}

export function SearchBox({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  const router = useRouter();
  const listId = useId();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<{ query: string; data: Suggestions } | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const trimmed = query.trim();

  useEffect(() => {
    if (trimmed.length < MIN_LENGTH) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetchSuggestions(trimmed, controller.signal)
        .then((data) => setResult({ query: trimmed, data }))
        .catch(() => undefined); // подсказки необязательны: полный поиск по Enter всё равно работает
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [trimmed]);

  const data = result && result.query === trimmed ? result.data : null;
  const options = data ? toOptions(data, lang) : [];
  const expanded = open && trimmed.length >= MIN_LENGTH && data !== null;

  function go(href: string) {
    setOpen(false);
    setActive(-1);
    router.push(href);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((index) => Math.min(index + 1, options.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, -1));
    } else if (event.key === "Enter" && expanded && options[active]) {
      event.preventDefault();
      go(options[active].href);
    } else if (event.key === "Escape") {
      setOpen(false);
      setActive(-1);
    }
  }

  return (
    <Form action={`/${lang}/search`} role="search" className={styles.form}>
      <input
        className={styles.input}
        type="search"
        name="q"
        value={query}
        placeholder={dict.searchPlaceholder}
        aria-label={dict.searchSubmit}
        autoComplete="off"
        role="combobox"
        aria-expanded={expanded}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={expanded && active >= 0 ? `${listId}-${active}` : undefined}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      <button className={styles.submit} type="submit">
        {dict.searchSubmit}
      </button>
      <ul id={listId} role="listbox" className={styles.list} hidden={!expanded}>
        {expanded && options.length === 0 && (
          <li role="presentation" className={styles.empty}>
            {dict.searchNothing}
          </li>
        )}
        {expanded &&
          options.map((option, index) => (
            <li
              key={option.href}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              className={index === active ? styles.activeOption : styles.option}
              onMouseDown={(event) => {
                event.preventDefault();
                go(option.href);
              }}
            >
              <span>{option.label}</span>
              <span className={styles.meta}>{option.meta}</span>
            </li>
          ))}
      </ul>
    </Form>
  );
}
