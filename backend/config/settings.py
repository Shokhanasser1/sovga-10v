from decimal import Decimal
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.core",
    "apps.catalog",
    "apps.sourcing",
    "apps.inventory",
    "apps.pricing",
    "apps.promo",
    "apps.customers",
    "apps.notifications",
    "apps.orders",
    "apps.payments",
    "apps.bot",
    "apps.delivery",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if env("DATABASE_URL", default=None):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский"), ("uz", "Oʻzbekcha")]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Только сессия с CSRF: вход по паролю через Basic Auth в API не нужен никому
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": ["apps.core.throttling.ClientRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        # В разработке витрина и браузер приходят с 127.0.0.1 и делят один счётчик — лимиты шире
        "anon": env("THROTTLE_ANON", default="2000/min" if DEBUG else "120/min"),
        "search": env("THROTTLE_SEARCH", default="1000/min" if DEBUG else "60/min"),
        "otp": env("THROTTLE_OTP", default="100/min" if DEBUG else "10/min"),
    },
}

# Витрина обращается к API прямо из браузера — только с этих адресов
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://127.0.0.1:3000"]
)

# Браузер отправляет cookie сессии в API (вход по коду) — нужны CORS с cookie и доверенные источники CSRF
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

# Адреса своих прокси (nginx на этом же сервере): им доверяем заголовок X-Real-IP
TRUSTED_PROXIES = env.list("TRUSTED_PROXIES", default=["127.0.0.1", "::1"])
# Общий секрет с витриной Next.js: её серверные запросы не ограничиваются. Пусто — лимит для всех.
INTERNAL_API_TOKEN = env("INTERNAL_API_TOKEN", default="")

# Комиссия эквайринга (Payme/Click) в процентах — уменьшает бюджет подарка
CARD_COMMISSION_PCT = Decimal(env("CARD_COMMISSION_PCT", default="0"))
# Комиссия провайдера рассрочки в процентах — бюджет подарка в рассрочку меньше
INSTALLMENT_COMMISSION_PCT = Decimal(env("INSTALLMENT_COMMISSION_PCT", default="5"))

# Коды входа: Telegram Gateway, запасной канал — SMS через Eskiz
TELEGRAM_GATEWAY_TOKEN = env("TELEGRAM_GATEWAY_TOKEN", default="")
ESKIZ_EMAIL = env("ESKIZ_EMAIL", default="")
ESKIZ_PASSWORD = env("ESKIZ_PASSWORD", default="")
ESKIZ_FROM = env("ESKIZ_FROM", default="4546")
OTP_SMS_TEMPLATE = env("OTP_SMS_TEMPLATE", default="Sovga: kirish kodi {code}")
# Только для сквозных тестов в режиме разработки
OTP_FIXED_CODE = env("OTP_FIXED_CODE", default="")
if OTP_FIXED_CODE and not DEBUG:
    raise ImproperlyConfigured("OTP_FIXED_CODE допустим только при DEBUG=true")

# Telegram-бот: уведомления менеджерам (новый заказ и т. п.). Токен — только из окружения.
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
# Имя бота без @ — для ссылок t.me/<имя>?start=…
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
MANAGER_CHAT_IDS = env.list("MANAGER_CHAT_IDS", default=[])

# Payme: касса и ключ (тестовый ключ — для test.paycom.uz). Без ключа вызовы Payme отклоняются.
PAYME_MERCHANT_ID = env("PAYME_MERCHANT_ID", default="")
PAYME_KEY = env("PAYME_KEY", default="")
PAYME_ACCOUNT_FIELD = env("PAYME_ACCOUNT_FIELD", default="order_id")
PAYME_CHECKOUT_URL = env("PAYME_CHECKOUT_URL", default="https://checkout.paycom.uz")
# Click: сервис, мерчант и секрет для подписи
CLICK_SERVICE_ID = env("CLICK_SERVICE_ID", default="")
CLICK_MERCHANT_ID = env("CLICK_MERCHANT_ID", default="")
CLICK_SECRET_KEY = env("CLICK_SECRET_KEY", default="")
CLICK_PAY_URL = env("CLICK_PAY_URL", default="https://my.click.uz/services/pay")
# НДС в фискальном чеке, % (уточнить у бухгалтера)
FISCAL_VAT_PERCENT = env.int("FISCAL_VAT_PERCENT", default=12)
# Адрес витрины — для возврата покупателя после оплаты
SITE_URL = env("SITE_URL", default="http://localhost:3000")
