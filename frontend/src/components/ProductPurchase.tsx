"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { fetchOffers } from "@/lib/api-client";
import { addToCart } from "@/lib/cart-store";
import { addToCompare, removeFromCompare } from "@/lib/compare-store";
import { deliveryText, formatSum, formatValue } from "@/lib/format";
import { SWATCHES, getDictionary, localized, type Locale } from "@/lib/i18n";
import type { ProductDetail, VariantOffer } from "@/lib/schemas";
import { useCompare } from "@/lib/use-compare";
import { axesOf, chooseValue, optionState, variantLabel } from "@/lib/variants";

import { DeviceArt, kindFor } from "./DeviceArt";
import { IkatRibbon } from "./IkatRibbon";
import styles from "./ProductPurchase.module.css";
import { SpecsTable } from "./SpecsTable";

type Offers = Record<string, VariantOffer>;

const STATE_CLASS = {
  selected: styles.selected,
  available: "",
  "other-combination": styles.otherCombination,
};

export function ProductPurchase({ product, lang }: { product: ProductDetail; lang: Locale }) {
  const dict = getDictionary(lang);
  const axes = useMemo(() => axesOf(product), [product]);
  const [sku, setSku] = useState(product.variants[0]?.sku ?? "");
  const [offers, setOffers] = useState<Offers | null>(null);
  const [offersFailed, setOffersFailed] = useState(false);
  const picked = useRef(false);
  const compare = useCompare();
  const router = useRouter();
  const [cartFull, setCartFull] = useState(false);

  useEffect(() => {
    fetchOffers(product.slug)
      .then((list) => {
        const map = Object.fromEntries(list.map((item) => [item.sku, item]));
        setOffers(map);
        if (picked.current) return;
        // Пока покупатель ничего не выбрал, показываем вариант, который можно купить.
        setSku((current) =>
          map[current]?.availability.status !== "out_of_stock"
            ? current
            : (list.find((item) => item.availability.status !== "out_of_stock")?.sku ?? current),
        );
      })
      .catch(() => setOffersFailed(true));
  }, [product.slug]);

  const variant = product.variants.find((item) => item.sku === sku) ?? product.variants[0];
  if (!variant) return null;
  const offer = offers?.[variant.sku];
  const color = typeof variant.axes.color === "string" ? SWATCHES[variant.axes.color] : undefined;
  const inCompare = compare.some((item) => item.sku === variant.sku);

  function buy() {
    const added = addToCart({
      sku: variant.sku,
      slug: product.slug,
      name_ru: product.name_ru,
      name_uz: product.name_uz,
      variantLabel: variantLabel(variant, axes, lang),
    });
    if (added) router.push(`/${lang}/cart`);
    else setCartFull(true);
  }

  function toggleCompare() {
    if (inCompare) {
      removeFromCompare(variant.sku);
      return;
    }
    addToCompare({
      sku: variant.sku,
      slug: product.slug,
      category: product.category,
      name_ru: product.name_ru,
      name_uz: product.name_uz,
      variantLabel: variantLabel(variant, axes, lang),
    });
  }

  return (
    <>
      <div className={styles.purchase}>
        <div className={styles.media}>
          <DeviceArt kind={kindFor(product.category)} color={color} label={product.brand.name} className={styles.art} />
        </div>
        <div className={styles.info}>
          <p className={styles.brand}>{product.brand.name}</p>
          <h1 className={`display ${styles.name}`}>{localized(product, lang)}</h1>

          {axes.map((axis) => (
            <fieldset key={axis.code} className={styles.axis}>
              <legend>{localized(axis, lang)}</legend>
              <div className={styles.options}>
                {axis.values.map((value) => {
                  const state = optionState(product.variants, variant, axes, axis.code, value);
                  const target = chooseValue(product.variants, variant, axes, axis.code, value, offers);
                  const soldOut = offers?.[target.sku]?.availability.status === "out_of_stock";
                  const swatch = typeof value === "string" ? SWATCHES[value] : undefined;
                  return (
                    <button
                      key={String(value)}
                      type="button"
                      aria-pressed={state === "selected"}
                      className={[styles.option, STATE_CLASS[state], soldOut ? styles.soldOut : ""].join(" ")}
                      onClick={() => {
                        picked.current = true;
                        setSku(target.sku);
                      }}
                    >
                      {swatch && <span className={styles.swatch} style={{ background: swatch }} aria-hidden="true" />}
                      {formatValue(value, axis.unit, lang)}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          ))}

          {variant.axes.sim === "esim_only" && (
            <p className={styles.warning} role="note">
              {dict.esimOnlyWarning}
            </p>
          )}

          <div className={styles.priceBlock} aria-live="polite">
            <p className={`price ${styles.price}`}>
              {offer?.price_uzs ? formatSum(offer.price_uzs, lang) : offers || offersFailed ? dict.noPrice : "…"}
            </p>
            {offer && (
              <p className={offer.availability.status === "out_of_stock" ? styles.unavailable : styles.available}>
                {deliveryText(offer.availability.status, offer.availability.lead_time_days, lang)}
              </p>
            )}
          </div>

          {offer && offer.gift_budget_uzs > 0 && (
            <div className={styles.gift}>
              <IkatRibbon orientation="horizontal" length={900} className={styles.giftRibbon} />
              <p className={styles.giftText}>
                <strong>{dict.gift(formatSum(offer.gift_budget_uzs, lang))}</strong>
                <span>{dict.giftHint}</span>
              </p>
            </div>
          )}

          <p className={styles.delivery}>{dict.freeDelivery}</p>

          <div className={styles.actions}>
            <button
              className="button"
              type="button"
              disabled={!offer?.price_uzs || offer.availability.status === "out_of_stock"}
              onClick={buy}
            >
              {dict.buy}
            </button>
            <button className="button button-ghost" type="button" aria-pressed={inCompare} onClick={toggleCompare}>
              {inCompare ? dict.inCompare : dict.addToCompare}
            </button>
          </div>
          {cartFull && (
            <p className={styles.note} role="alert">
              {dict.cartFull}
            </p>
          )}
        </div>
      </div>

      <section className={styles.specsSection}>
        <h2 className={`display ${styles.sectionTitle}`}>{dict.specs}</h2>
        <SpecsTable
          definitions={product.attribute_definitions}
          values={{ ...product.attributes, ...variant.axes, ...variant.attributes }}
          lang={lang}
        />
      </section>
    </>
  );
}
