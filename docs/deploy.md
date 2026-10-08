# Запуск на сервере (без Docker)

Схема: nginx (HTTPS) → Django через gunicorn на `127.0.0.1:8000` (API, админка, колбэки оплаты) и витрина Next.js на `127.0.0.1:3000`; Telegram-бот — отдельная служба; фоновые задачи — cron каждые 15 минут; база — PostgreSQL с ежедневной копией. Готовые файлы — в папке `deploy/`.

## 0. Что нужно заранее

- Сервер Ubuntu 24.04 (2 ядра, 4 ГБ памяти хватит на старт) — **в Узбекистане**: персональные данные граждан по закону хранятся в стране.
- Домен, направленный на сервер (A-запись), например `sovga.uz`.
- Ключи: Payme (касса и ключ), Click (service id, merchant id, секрет), коды входа (Telegram Gateway и/или Eskiz), **новый** токен Telegram-бота и его имя.

## 1. Пакеты

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libpq-dev postgresql nginx git certbot python3-certbot-nginx
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
```

## 2. Пользователь и код

```bash
sudo adduser --system --group --home /srv/sovga sovga
sudo -u sovga git clone <адрес репозитория> /srv/sovga
```

## 3. База

```bash
sudo -u postgres psql -c "CREATE USER sovga WITH PASSWORD '<длинный пароль>';"
sudo -u postgres psql -c "CREATE DATABASE sovga OWNER sovga;"
```

## 4. Настройки Django — `/srv/sovga/backend/.env`

Начните с `backend/.env.example`. Обязательно для боевого режима:

```
DEBUG=false
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=sovga.uz,www.sovga.uz,127.0.0.1
DATABASE_URL=postgres://sovga:<пароль>@localhost:5432/sovga
CORS_ALLOWED_ORIGINS=https://sovga.uz,https://www.sovga.uz
SITE_URL=https://sovga.uz
INTERNAL_API_TOKEN=<длинная случайная строка, та же — во frontend>
TELEGRAM_GATEWAY_TOKEN=...        # и/или ESKIZ_EMAIL, ESKIZ_PASSWORD
TELEGRAM_BOT_TOKEN=...            # новый токен от @BotFather
TELEGRAM_BOT_USERNAME=...         # имя бота без @
MANAGER_CHAT_IDS=...              # номера чатов менеджеров: напишите боту /id
PAYME_MERCHANT_ID=...  PAYME_KEY=...
CLICK_SERVICE_ID=...  CLICK_MERCHANT_ID=...  CLICK_SECRET_KEY=...
```

`127.0.0.1` в `ALLOWED_HOSTS` нужен витрине: её серверная отрисовка ходит в Django напрямую. `OTP_FIXED_CODE` в боевом режиме запрещён — с ним сервер не запустится. Права на файл: `sudo chmod 600 /srv/sovga/backend/.env && sudo chown sovga /srv/sovga/backend/.env`.

## 5. Django

```bash
cd /srv/sovga/backend
sudo -u sovga python3 -m venv .venv
sudo -u sovga .venv/bin/pip install -r requirements.txt
sudo -u sovga .venv/bin/python manage.py migrate
sudo -u sovga .venv/bin/python manage.py collectstatic --noinput
sudo -u sovga .venv/bin/python manage.py createsuperuser
sudo -u sovga .venv/bin/python manage.py check --deploy    # должно быть без замечаний
```

## 6. Витрина — `/srv/sovga/frontend/.env.production.local`

```
API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_URL=
SITE_URL=https://sovga.uz
INTERNAL_API_TOKEN=<та же строка, что в backend/.env>
```

`NEXT_PUBLIC_API_URL` пустой: браузер ходит в `/api/` этого же сайта, а nginx отдаёт его Django. Он вшивается при сборке — после изменения пересоберите.

```bash
cd /srv/sovga/frontend
sudo -u sovga npm ci
sudo -u sovga npm run build
```

## 7. Службы

```bash
sudo cp /srv/sovga/deploy/systemd/sovga-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sovga-api sovga-web sovga-bot
systemctl status sovga-api sovga-web sovga-bot
```

Логи: `journalctl -u sovga-api -f` (так же `sovga-web`, `sovga-bot`).

## 8. nginx и HTTPS

```bash
sudo cp /srv/sovga/deploy/nginx/sovga.conf /etc/nginx/sites-available/sovga
sudo sed -i 's/sovga.uz/<ваш домен>/g' /etc/nginx/sites-available/sovga
sudo ln -s /etc/nginx/sites-available/sovga /etc/nginx/sites-enabled/sovga
sudo rm -f /etc/nginx/sites-enabled/default
sudo certbot certonly --nginx -d <ваш домен> -d www.<ваш домен>
sudo nginx -t && sudo systemctl reload nginx
```

HSTS включён на 30 дней (`SECURE_HSTS_SECONDS`). Поддомены и список предзагрузки браузеров (`SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`) — только когда все поддомены точно работают по HTTPS: отменить это трудно.

## 9. Фоновые задачи и копии базы

```bash
sudo install -d -m 700 -o postgres -g postgres /var/backups/sovga   # копии с данными покупателей — только для postgres
sudo cp /srv/sovga/deploy/cron/sovga /etc/cron.d/sovga
```

Логи задач: `journalctl -t sovga-jobs`. Восстановить копию: `sudo -u postgres pg_restore --clean -d sovga /var/backups/sovga/sovga-<дата>.dump`. Копии стоит дополнительно уносить с сервера (другой сервер или облако) — в зашифрованном виде.

## 10. Кабинеты платёжных систем

- Payme: адрес Merchant API — `https://<домен>/api/v1/payments/payme/`.
- Click: Prepare — `https://<домен>/api/v1/payments/click/prepare/`, Complete — `https://<домен>/api/v1/payments/click/complete/`.
- Сначала проверьте в песочницах (для Payme `PAYME_CHECKOUT_URL=https://test.paycom.uz`), потом переключите на боевые ключи.

## 11. Первый день

1. Админка `https://<домен>/admin`: категории, товары, поставщики (колонки прайса), правила наценки, политика подарков.
2. Поставщикам с Telegram: Админка → Поставщики → действие «Ссылка для подключения Telegram-бота».
3. Сотрудникам — отдельные учётные записи с нужными правами: оператору — «изменять заказы», бухгалтеру — «view выгрузка для бухгалтера».
4. Тестовый заказ на маленькую сумму: оплата → сборка → передача курьеру → доставка.

## Обновление

```bash
cd /srv/sovga && sudo -u sovga git pull
cd backend && sudo -u sovga .venv/bin/pip install -r requirements.txt
sudo -u sovga .venv/bin/python manage.py migrate
sudo -u sovga .venv/bin/python manage.py collectstatic --noinput
cd ../frontend && sudo -u sovga npm ci && sudo -u sovga npm run build
sudo systemctl restart sovga-api sovga-web sovga-bot
```
