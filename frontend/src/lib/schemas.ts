/** Схемы ответов Django API. Всё, что приходит снаружи, проходит через них. */

import { z } from "zod";

const attrValue = z.union([z.string(), z.number(), z.boolean()]);
const attrMap = z.record(z.string(), attrValue);

export const brandSchema = z.object({ slug: z.string(), name: z.string() });

export const categorySchema = z.object({
  id: z.number(),
  slug: z.string(),
  name_ru: z.string(),
  name_uz: z.string(),
  parent: z.number().nullable(),
  is_serialized: z.boolean(),
});

export const productSummarySchema = z.object({
  slug: z.string(),
  name_ru: z.string(),
  name_uz: z.string(),
  brand: brandSchema,
  category: z.string(),
  is_accessory: z.boolean(),
  price_from_uzs: z.number().nullable(),
  is_available: z.boolean(),
});

export const pageSchema = <T extends z.ZodType>(item: T) =>
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(item),
  });

export const attributeDefinitionSchema = z.object({
  code: z.string(),
  name_ru: z.string(),
  name_uz: z.string(),
  unit: z.string(),
  type: z.enum(["number", "enum", "bool", "text"]),
  level: z.enum(["model", "variant"]),
  is_variant_axis: z.boolean(),
  comparison: z.enum(["higher_better", "lower_better", "none"]),
});

export const variantSchema = z.object({
  sku: z.string(),
  axes: attrMap,
  attributes: attrMap,
  images: z.array(z.string()),
  giftable: z.boolean(),
});

export const productDetailSchema = productSummarySchema.extend({
  description_ru: z.string(),
  description_uz: z.string(),
  attributes: attrMap,
  seo_title_ru: z.string(),
  seo_title_uz: z.string(),
  seo_description_ru: z.string(),
  seo_description_uz: z.string(),
  variants: z.array(variantSchema),
  attribute_definitions: z.array(attributeDefinitionSchema),
});

export const facetsSchema = z.object({
  brands: z.array(z.object({ slug: z.string(), name: z.string(), count: z.number() })),
  attributes: z.array(
    z.object({
      code: z.string(),
      name_ru: z.string(),
      name_uz: z.string(),
      unit: z.string(),
      type: z.enum(["number", "enum", "bool", "text"]),
      values: z.array(z.object({ value: attrValue, count: z.number() })),
    }),
  ),
  price: z.object({ min: z.number().nullable(), max: z.number().nullable() }),
});

export const variantOfferSchema = z.object({
  sku: z.string(),
  price_uzs: z.number().nullable(),
  availability: z.object({
    status: z.enum(["in_stock", "on_order", "out_of_stock"]),
    lead_time_days: z.number().nullable(),
  }),
  gift_budget_uzs: z.number(),
});

export const suggestSchema = z.object({
  products: z.array(productSummarySchema),
  categories: z.array(categorySchema),
});

export const comparisonRowSchema = z.object({
  code: z.string(),
  name: z.string(),
  unit: z.string(),
  values: z.array(attrValue.nullable()),
  best: z.array(z.number()),
});

export type Category = z.infer<typeof categorySchema>;
export type ProductSummary = z.infer<typeof productSummarySchema>;
export type ProductDetail = z.infer<typeof productDetailSchema>;
export type AttributeDefinition = z.infer<typeof attributeDefinitionSchema>;
export type Variant = z.infer<typeof variantSchema>;
export type Facets = z.infer<typeof facetsSchema>;
export type VariantOffer = z.infer<typeof variantOfferSchema>;
export type Suggestions = z.infer<typeof suggestSchema>;
export type ComparisonRow = z.infer<typeof comparisonRowSchema>;
export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };

// --- Вход, корзина, заказы ---

export const customerSchema = z.object({ phone: z.string(), name: z.string(), language: z.string() });
export const meSchema = z.object({ customer: customerSchema.nullable() });
export const codeSentSchema = z.object({ sent: z.boolean(), channel: z.string(), resend_after: z.number() });

const giftOptionSchema = z.object({
  sku: z.string(),
  name_ru: z.string(),
  name_uz: z.string(),
  price_uzs: z.number(),
  axes: attrMap.default({}),
});

export const quoteSchema = z.object({
  lines: z.array(
    z.object({
      sku: z.string(),
      slug: z.string().nullable(),
      name_ru: z.string().nullable(),
      name_uz: z.string().nullable(),
      qty: z.number(),
      unit_price_uzs: z.number().nullable(),
      line_total_uzs: z.number(),
      availability: z.string(),
      gift_budget_uzs: z.number(),
      gift_options: z.array(giftOptionSchema),
      gift: giftOptionSchema.nullable(),
      errors: z.array(z.string()),
    }),
  ),
  total_uzs: z.number(),
  errors: z.array(z.string()),
  can_order: z.boolean(),
});

export const ORDER_STATUSES = [
  "sourcing", "confirmed", "awaiting_payment", "paid", "installment_pending", "signed", "cod", "picking",
  "handed_to_carrier", "delivered", "completed", "cancelled", "return_requested", "inspected", "refunded",
] as const;
export const orderStatusSchema = z.enum(ORDER_STATUSES);

export const orderSchema = z.object({
  number: z.string(),
  status: orderStatusSchema,
  payment_method: z.string(),
  total_uzs: z.number(),
  price_lock_until: z.string(),
  created_at: z.string(),
  address_text: z.string(),
  address_landmark: z.string(),
  comment: z.string(),
  can_cancel: z.boolean(),
  can_pay: z.boolean(),
  pay_providers: z.array(z.enum(["payme", "click"])),
  telegram: z.enum(["linked", "available", "off"]),
  shipment: z
    .object({
      carrier: z.enum(["own", "service"]),
      courier_name: z.string(),
      courier_phone: z.string(),
      service_name: z.string(),
      tracking: z.string(),
    })
    .nullable(),
  lines: z.array(
    z.object({
      sku: z.string(),
      slug: z.string(),
      name_ru: z.string(),
      name_uz: z.string(),
      qty: z.number(),
      price_uzs: z.number(),
      is_gift: z.boolean(),
      axes: attrMap.default({}),
      devices: z.array(z.object({ imei: z.string(), warranty_until: z.string() })).default([]),
    }),
  ),
  events: z.array(z.object({ status: orderStatusSchema, note: z.string(), at: z.string() })),
});

export type Customer = z.infer<typeof customerSchema>;
export type Quote = z.infer<typeof quoteSchema>;
export type QuoteLine = Quote["lines"][number];
export type GiftOption = z.infer<typeof giftOptionSchema>;
export type Order = z.infer<typeof orderSchema>;
export type OrderStatus = z.infer<typeof orderStatusSchema>;
