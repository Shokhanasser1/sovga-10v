import { getDictionary, localized, type Locale } from "@/lib/i18n";
import type { ProductDetail, VariantOffer } from "@/lib/schemas";

const AVAILABILITY = {
  in_stock: "https://schema.org/InStock",
  on_order: "https://schema.org/PreOrder",
  out_of_stock: "https://schema.org/OutOfStock",
};

function bestAvailability(offers: VariantOffer[]): string {
  const statuses = new Set(offers.map((offer) => offer.availability.status));
  if (statuses.has("in_stock")) return AVAILABILITY.in_stock;
  if (statuses.has("on_order")) return AVAILABILITY.on_order;
  return AVAILABILITY.out_of_stock;
}

/** Разметка schema.org/Product: название, бренд, диапазон цен в сумах и наличие. */
export function ProductJsonLd({
  product,
  offers,
  lang,
}: {
  product: ProductDetail;
  offers: VariantOffer[];
  lang: Locale;
}) {
  const name = localized(product, lang);
  const prices = offers.map((offer) => offer.price_uzs).filter((price): price is number => price !== null);
  const data = {
    "@context": "https://schema.org",
    "@type": "Product",
    name,
    description: getDictionary(lang).productDescription(name),
    brand: { "@type": "Brand", name: product.brand.name },
    sku: product.variants[0]?.sku,
    ...(prices.length > 0 && {
      offers: {
        "@type": "AggregateOffer",
        priceCurrency: "UZS",
        lowPrice: Math.min(...prices),
        highPrice: Math.max(...prices),
        offerCount: prices.length,
        availability: bestAvailability(offers),
      },
    }),
  };
  return (
    <script
      type="application/ld+json"
      // Экранируем «<», чтобы текст из базы не мог закрыть тег script.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}
