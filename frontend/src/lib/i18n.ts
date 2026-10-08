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
  ordersShort: "Заказы",
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
  productDescription: (name: string) =>
    `${name} — с подарком: чехол, защитное стекло или зарядка на выбор. Доставка по Узбекистану бесплатно.`,
  cart: "Корзина",
  cartEmpty: "Корзина пуста. Загляните в каталог — к каждому смартфону подарок.",
  cartFull: "В корзине уже 10 позиций — оформите заказ или уберите что-нибудь.",
  added: "Добавлено в корзину",
  qty: "Количество",
  less: "Меньше",
  more: "Больше",
  remove: "Убрать",
  giftChoose: (amount: string) => `Подарок до ${amount} — выберите`,
  noGift: "Без подарка",
  yourGift: "Ваш подарок",
  total: "Итого",
  toCheckout: "Оформить заказ",
  login: "Вход",
  loginLead: "Пришлём код в Telegram или по SMS — пароль не нужен.",
  phone: "Номер телефона",
  phonePlaceholder: "+998 90 123 45 67",
  getCode: "Получить код",
  codeSent: (channel: string): string =>
    channel === "telegram" ? "Код отправлен в Telegram" : channel === "sms" ? "Код отправлен по SMS" : "Код отправлен",
  code: "Код из сообщения",
  signIn: "Войти",
  resendIn: (seconds: number) => `Новый код — через ${seconds} с`,
  resend: "Отправить код ещё раз",
  changePhone: "Другой номер",
  account: "Мои заказы",
  logout: "Выйти",
  ordersEmpty: "Заказов пока нет.",
  checkout: "Оформление заказа",
  address: "Адрес доставки",
  addressPlaceholder: "Город, район, улица, дом, квартира",
  landmark: "Ориентир для курьера",
  landmarkPlaceholder: "Например: напротив школы №110",
  comment: "Комментарий",
  commentPlaceholder: "Удобное время, этаж, домофон",
  payment: "Оплата",
  paymentCard: "Картой онлайн — Payme или Click, после подтверждения заказа",
  placeOrder: "Подтвердить заказ",
  sending: "Отправляем…",
  orderTitle: (number: string) => `Заказ ${number}`,
  cancelOrder: "Отменить заказ",
  payNext: "Онлайн-оплата сейчас недоступна — менеджер свяжется с вами для оплаты.",
  payWith: (provider: string) => `Оплатить через ${provider}`,
  payRedirect: "Переходим к оплате…",
  telegramConnect: "Получать статусы в Telegram",
  telegramLinked: "Статусы заказа приходят в Telegram",
  deliveryCourier: (name: string) => `Курьер ${name}`,
  warranty: (imei: string, until: string) => `IMEI ${imei} · гарантия до ${until}`,
  deliveryService: (service: string, tracking: string) => `${service}, накладная ${tracking}`,
  priceLocked: (time: string) => `Цена закреплена до ${time}`,
  giftLabel: "подарок",
  free: "бесплатно",
  orderStatus: {
    sourcing: "Проверяем наличие у поставщика",
    confirmed: "Ждёт оплаты",
    awaiting_payment: "Ждём поступления оплаты",
    paid: "Оплачен",
    installment_pending: "Оформляется рассрочка",
    signed: "Рассрочка оформлена",
    cod: "Оплата при получении",
    picking: "Собираем заказ",
    handed_to_carrier: "Передан курьеру",
    delivered: "Доставлен",
    completed: "Завершён",
    cancelled: "Отменён",
    return_requested: "Оформляется возврат",
    inspected: "Возврат проверен",
    refunded: "Деньги возвращены",
  },
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
  ordersShort: "Buyurtmalar",
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
  productDescription: (name: string) =>
    `${name} — sovgʻa bilan: gʻilof, himoya oynasi yoki quvvatlagich. Oʻzbekiston boʻylab yetkazib berish bepul.`,
  cart: "Savat",
  cartEmpty: "Savat boʻsh. Katalogga qarang — har bir smartfonga sovgʻa.",
  cartFull: "Savatda allaqachon 10 ta pozitsiya bor — buyurtma bering yoki birortasini olib tashlang.",
  added: "Savatga qoʻshildi",
  qty: "Soni",
  less: "Kamroq",
  more: "Koʻproq",
  remove: "Olib tashlash",
  giftChoose: (amount: string) => `${amount}gacha sovgʻa — tanlang`,
  noGift: "Sovgʻasiz",
  yourGift: "Sovgʻangiz",
  total: "Jami",
  toCheckout: "Buyurtma berish",
  login: "Kirish",
  loginLead: "Kodni Telegram yoki SMS orqali yuboramiz — parol kerak emas.",
  phone: "Telefon raqami",
  phonePlaceholder: "+998 90 123 45 67",
  getCode: "Kod olish",
  codeSent: (channel: string) =>
    channel === "telegram" ? "Kod Telegramga yuborildi" : channel === "sms" ? "Kod SMS orqali yuborildi" : "Kod yuborildi",
  code: "Xabardagi kod",
  signIn: "Kirish",
  resendIn: (seconds: number) => `Yangi kod — ${seconds} soniyadan keyin`,
  resend: "Kodni qayta yuborish",
  changePhone: "Boshqa raqam",
  account: "Buyurtmalarim",
  logout: "Chiqish",
  ordersEmpty: "Hozircha buyurtmalar yoʻq.",
  checkout: "Buyurtmani rasmiylashtirish",
  address: "Yetkazib berish manzili",
  addressPlaceholder: "Shahar, tuman, koʻcha, uy, xonadon",
  landmark: "Kuryer uchun moʻljal",
  landmarkPlaceholder: "Masalan: 110-maktab roʻparasida",
  comment: "Izoh",
  commentPlaceholder: "Qulay vaqt, qavat, domofon",
  payment: "Toʻlov",
  paymentCard: "Onlayn karta orqali — Payme yoki Click, buyurtma tasdiqlangach",
  placeOrder: "Buyurtmani tasdiqlash",
  sending: "Yuborilmoqda…",
  orderTitle: (number: string) => `Buyurtma ${number}`,
  cancelOrder: "Buyurtmani bekor qilish",
  payNext: "Onlayn toʻlov hozircha mavjud emas — toʻlov uchun menejer siz bilan bogʻlanadi.",
  payWith: (provider: string) => `${provider} orqali toʻlash`,
  payRedirect: "Toʻlovga oʻtyapmiz…",
  telegramConnect: "Holatlarni Telegramda olish",
  telegramLinked: "Buyurtma holatlari Telegramga keladi",
  deliveryCourier: (name: string) => `Kuryer ${name}`,
  warranty: (imei: string, until: string) => `IMEI ${imei} · kafolat ${until} gacha`,
  deliveryService: (service: string, tracking: string) => `${service}, yuk xati ${tracking}`,
  priceLocked: (time: string) => `Narx ${time} gacha qotirilgan`,
  giftLabel: "sovgʻa",
  free: "bepul",
  orderStatus: {
    sourcing: "Yetkazib beruvchida mavjudligini tekshiryapmiz",
    confirmed: "Toʻlov kutilmoqda",
    awaiting_payment: "Toʻlov tushishini kutyapmiz",
    paid: "Toʻlangan",
    installment_pending: "Muddatli toʻlov rasmiylashtirilmoqda",
    signed: "Muddatli toʻlov rasmiylashtirildi",
    cod: "Qabul qilishda toʻlov",
    picking: "Buyurtma yigʻilmoqda",
    handed_to_carrier: "Kuryerga topshirildi",
    delivered: "Yetkazildi",
    completed: "Yakunlandi",
    cancelled: "Bekor qilindi",
    return_requested: "Qaytarish rasmiylashtirilmoqda",
    inspected: "Qaytarish tekshirildi",
    refunded: "Pul qaytarildi",
  },
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
