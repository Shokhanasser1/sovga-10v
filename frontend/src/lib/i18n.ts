export const LOCALES = ["ru", "uz"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "ru";

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

const ru = {
  shopName: "Sovgʻa",
  languageName: "Русский",
  searchPlaceholder: "Поиск: iPhone 16, Galaxy, чехол…",
  searchSubmit: "Найти",
  searchNothing: "Ничего не нашли. Проверьте написание или откройте каталог.",
  searchProducts: "Товары",
  searchCategories: "Категории",
  catalog: "Каталог",
  compare: "Сравнение",
  heroTitle: "Каждый смартфон — с подарком",
  heroText: "Чехол, стекло или зарядка на выбор. Доставка бесплатно.",
  heroGiftTag: "подарок к смартфону",
  toCatalog: "Перейти в каталог",
  categoriesTitle: "Категории",
  availableTitle: "Есть в наличии",
  priceFrom: "от",
  noPrice: "Цена уточняется",
  inStock: "В наличии",
  onSale: "В продаже",
  onOrder: "Под заказ",
  outOfStock: "Нет в наличии",
  deliveryToday: "доставим сегодня",
  deliveryTomorrow: "доставим завтра",
  deliveryIn: (days: number) => `доставим за ${days} ${pluralRu(days, "день", "дня", "дней")}`,
  gift: (amount: string) => `Подарок до ${amount}`,
  giftHint: "Чехол, защитное стекло или зарядка — выберете при оформлении",
  freeDelivery: "Доставка бесплатно",
  buy: "Купить",
  buySoon: "Оформление заказа появится на следующем этапе",
  addToCompare: "Сравнить",
  inCompare: "В сравнении",
  specs: "Характеристики",
  accessories: "Подходят к этой модели",
  yes: "Да",
  no: "Нет",
  filters: "Фильтры",
  brand: "Бренд",
  price: "Цена, сум",
  priceMin: "от",
  priceMax: "до",
  onlyAvailable: "Только в наличии",
  apply: "Показать",
  reset: "Сбросить",
  sort: "Сортировка",
  sortRelevance: "По релевантности",
  sortName: "По названию",
  sortPriceAsc: "Сначала дешевле",
  sortPriceDesc: "Сначала дороже",
  found: (count: number) => `${count} ${pluralRu(count, "товар", "товара", "товаров")}`,
  emptyCatalog: "Под эти фильтры ничего не подошло. Уберите часть фильтров.",
  prev: "Назад",
  next: "Дальше",
  searchResults: (query: string) => `Поиск: «${query}»`,
  compareTitle: "Сравнение моделей",
  compareEmpty: "Добавьте модели кнопкой «Сравнить» на странице товара — до 4 штук.",
  compareOnlySameCategory: "Сравнивать можно модели одной категории.",
  compareRemove: "Убрать",
  compareBest: "лучшее значение",
  notFoundTitle: "Такой страницы нет",
  notFoundText: "Возможно, товар сняли с продажи. Попробуйте поиск.",
  apiDown: "Не удалось загрузить данные магазина. Проверьте, что сервер Django запущен.",
  retry: "Повторить",
};

export type Dictionary = typeof ru;

const uz: Dictionary = {
  shopName: "Sovgʻa",
  languageName: "Oʻzbekcha",
  searchPlaceholder: "Qidirish: iPhone 16, Galaxy, gʻilof…",
  searchSubmit: "Qidirish",
  searchNothing: "Hech narsa topilmadi. Yozilishini tekshiring yoki katalogni oching.",
  searchProducts: "Mahsulotlar",
  searchCategories: "Turkumlar",
  catalog: "Katalog",
  compare: "Taqqoslash",
  heroTitle: "Har bir smartfonga sovgʻa",
  heroText: "Gʻilof, himoya oynasi yoki quvvatlagich — tanlov sizda. Yetkazib berish bepul.",
  heroGiftTag: "smartfonga sovgʻa",
  toCatalog: "Katalogga oʻtish",
  categoriesTitle: "Turkumlar",
  availableTitle: "Sotuvda bor",
  priceFrom: "",
  noPrice: "Narx aniqlanmoqda",
  inStock: "Mavjud",
  onSale: "Sotuvda",
  onOrder: "Buyurtma asosida",
  outOfStock: "Mavjud emas",
  deliveryToday: "bugun yetkazamiz",
  deliveryTomorrow: "ertaga yetkazamiz",
  deliveryIn: (days: number) => `${days} kunda yetkazamiz`,
  gift: (amount: string) => `${amount}gacha sovgʻa`,
  giftHint: "Gʻilof, himoya oynasi yoki quvvatlagich — buyurtmada tanlaysiz",
  freeDelivery: "Yetkazib berish bepul",
  buy: "Sotib olish",
  buySoon: "Buyurtma berish keyingi bosqichda qoʻshiladi",
  addToCompare: "Taqqoslash",
  inCompare: "Taqqoslashda",
  specs: "Xususiyatlari",
  accessories: "Ushbu modelga mos",
  yes: "Ha",
  no: "Yoʻq",
  filters: "Filtrlar",
  brand: "Brend",
  price: "Narx, soʻm",
  priceMin: "dan",
  priceMax: "gacha",
  onlyAvailable: "Faqat mavjudlari",
  apply: "Koʻrsatish",
  reset: "Tozalash",
  sort: "Saralash",
  sortRelevance: "Mosligi boʻyicha",
  sortName: "Nomi boʻyicha",
  sortPriceAsc: "Avval arzonlari",
  sortPriceDesc: "Avval qimmatlari",
  found: (count: number) => `${count} ta mahsulot`,
  emptyCatalog: "Bu filtrlarga mos mahsulot yoʻq. Filtrlarning bir qismini olib tashlang.",
  prev: "Orqaga",
  next: "Keyingi",
  searchResults: (query: string) => `Qidiruv: «${query}»`,
  compareTitle: "Modellarni taqqoslash",
  compareEmpty: "Mahsulot sahifasidagi «Taqqoslash» tugmasi bilan 4 tagacha model qoʻshing.",
  compareOnlySameCategory: "Faqat bir turkumdagi modellarni taqqoslash mumkin.",
  compareRemove: "Olib tashlash",
  compareBest: "eng yaxshi qiymat",
  notFoundTitle: "Bunday sahifa yoʻq",
  notFoundText: "Ehtimol, mahsulot sotuvdan olingan. Qidiruvdan foydalaning.",
  apiDown: "Doʻkon maʼlumotlarini yuklab boʻlmadi. Django serveri ishga tushirilganini tekshiring.",
  retry: "Qayta urinish",
};

const DICTIONARIES: Record<Locale, Dictionary> = { ru, uz };

export function getDictionary(locale: Locale): Dictionary {
  return DICTIONARIES[locale];
}

export function pluralRu(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

/** Поле `name_ru` / `name_uz` объекта на нужном языке. */
export function localized(item: { name_ru: string; name_uz: string }, locale: Locale): string {
  return locale === "uz" ? item.name_uz || item.name_ru : item.name_ru;
}

/** Ссылка на тот же путь на другом языке: /ru/catalog → /uz/catalog. */
export function switchLocalePath(pathname: string, target: Locale): string {
  const parts = pathname.split("/");
  if (parts.length > 1 && isLocale(parts[1])) {
    parts[1] = target;
    return parts.join("/") || `/${target}`;
  }
  return `/${target}${pathname === "/" ? "" : pathname}`;
}

const ENUM_LABELS: Record<Locale, Record<string, string>> = {
  ru: {
    black: "Чёрный", white: "Белый", blue: "Синий", green: "Зелёный", titanium: "Титан",
    grey: "Серый", clear: "Прозрачный", nano_esim: "nano-SIM + eSIM", esim_only: "Только eSIM",
    dual_sim: "2 SIM", "usb-c": "USB-C", lightning: "Lightning",
  },
  uz: {
    black: "Qora", white: "Oq", blue: "Koʻk", green: "Yashil", titanium: "Titan", grey: "Kulrang",
    clear: "Shaffof", nano_esim: "nano-SIM + eSIM", esim_only: "Faqat eSIM", dual_sim: "2 SIM",
    "usb-c": "USB-C", lightning: "Lightning",
  },
};

const UNIT_LABELS: Record<string, string> = { ГБ: "GB", "мА·ч": "mA·soat", Вт: "Vt", г: "g" };

export function unitLabel(unit: string, locale: Locale): string {
  return locale === "uz" ? (UNIT_LABELS[unit] ?? unit) : unit;
}

export function enumLabel(value: string, locale: Locale): string {
  return ENUM_LABELS[locale][value] ?? value;
}

/** Цвета для образцов в выборе варианта. */
export const SWATCHES: Record<string, string> = {
  black: "#1d1f24", white: "#f2f2ee", blue: "#3b5b8f", green: "#5d7a5a", titanium: "#a39b8b",
  grey: "#7d828a", clear: "#e4ecef",
};
