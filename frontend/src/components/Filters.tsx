import Link from "next/link";

import { selectedValues, type SearchParams } from "@/lib/catalog-params";
import { formatValue } from "@/lib/format";
import { SWATCHES, getDictionary, localized, type Locale } from "@/lib/i18n";
import type { Facets } from "@/lib/schemas";

import styles from "./Filters.module.css";

export function Filters({
  facets,
  searchParams,
  lang,
  resetHref,
}: {
  facets: Facets;
  searchParams: SearchParams;
  lang: Locale;
  resetHref: string;
}) {
  const dict = getDictionary(lang);
  const brands = selectedValues(searchParams, "brand");
  const one = (key: string) => {
    const value = searchParams[key];
    return Array.isArray(value) ? value[0] : value;
  };
  return (
    <details className={styles.panel} open>
      <summary className={styles.summary}>{dict.filters}</summary>
      {facets.brands.length > 1 && (
        <fieldset className={styles.group}>
          <legend>{dict.brand}</legend>
          {facets.brands.map((brand) => (
            <label key={brand.slug} className={styles.option}>
              <input type="checkbox" name="brand" value={brand.slug} defaultChecked={brands.has(brand.slug)} />
              <span>{brand.name}</span>
              <span className={styles.count}>{brand.count}</span>
            </label>
          ))}
        </fieldset>
      )}
      {facets.attributes.map((attribute) => {
        const name = `f.${attribute.code}`;
        const chosen = selectedValues(searchParams, name);
        return (
          <fieldset key={attribute.code} className={styles.group}>
            <legend>{localized(attribute, lang)}</legend>
            {attribute.values.map(({ value, count }) => (
              <label key={String(value)} className={styles.option}>
                <input type="checkbox" name={name} value={String(value)} defaultChecked={chosen.has(String(value))} />
                {typeof value === "string" && SWATCHES[value] && (
                  <span className={styles.swatch} style={{ background: SWATCHES[value] }} aria-hidden="true" />
                )}
                <span>{formatValue(value, attribute.unit, lang)}</span>
                <span className={styles.count}>{count}</span>
              </label>
            ))}
          </fieldset>
        );
      })}
      <fieldset className={styles.group}>
        <legend>{dict.price}</legend>
        <div className={styles.range}>
          <input type="number" name="price_min" min={0} step={10000} inputMode="numeric"
            placeholder={`${dict.priceMin} ${facets.price.min ?? ""}`.trim()} defaultValue={one("price_min")}
            aria-label={`${dict.price} ${dict.priceMin}`} />
          <input type="number" name="price_max" min={0} step={10000} inputMode="numeric"
            placeholder={`${dict.priceMax} ${facets.price.max ?? ""}`.trim()} defaultValue={one("price_max")}
            aria-label={`${dict.price} ${dict.priceMax}`} />
        </div>
      </fieldset>
      <label className={styles.option}>
        <input type="checkbox" name="available" value="1" defaultChecked={one("available") === "1"} />
        <span>{dict.onlyAvailable}</span>
      </label>
      <div className={styles.actions}>
        <button className="button" type="submit">
          {dict.apply}
        </button>
        <Link href={resetHref} className={styles.reset}>
          {dict.reset}
        </Link>
      </div>
    </details>
  );
}
