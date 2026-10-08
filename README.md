# Sovgʻa — интернет-магазин электроники для Узбекистана

Смартфоны и техника с бесплатной доставкой и подарком на выбор (чехол, стекло, зарядка). Свой склад и товар поставщиков под заказ, цены в сумах по курсу ЦБ, оплата Payme и Click, учёт IMEI и гарантия, Telegram-бот для покупателей, поставщиков и менеджеров.

| Часть | Технологии | Где |
|---|---|---|
| API, админка, рабочее место оператора, бот | Python, Django 6, DRF | `backend/` |
| Витрина ru/uz | Next.js 16, React 19, TypeScript | `frontend/` |
| Проверка в браузере | Python Playwright | `e2e/` |
| Спецификация и планы | — | `docs/superpowers/` |
| Запуск на сервере | nginx, gunicorn, systemd, cron | `docs/deploy.md`, `deploy/` |

Docker не нужен: база по умолчанию SQLite, фоновые задачи — команда `run_jobs` по расписанию.

## Запуск на Windows

Нужны [Python 3.12+](https://www.python.org/downloads/) (при установке — галочка «Add python.exe to PATH») и [Node.js 20+](https://nodejs.org/).

```
scripts\setup.cmd
cd backend
.venv\Scripts\python.exe manage.py createsuperuser
cd ..
scripts\start.cmd
```

- `setup.cmd` — один раз: зависимости, `backend\.env` со своим секретным ключом, база, демо-каталог, сборка витрины.
- `start.cmd` — каждый раз: открывает окна API, витрины и (если в `backend\.env` есть токен) бота.
- Витрина — http://localhost:3000, админка — http://localhost:8000/admin, рабочее место оператора — в меню админки.
- Код входа: пока не настроены Telegram Gateway или Eskiz, он печатается в окне «Sovga — API».
- Фоновые задачи (прайсы, курс ЦБ, цены, просрочки, уведомления): вручную — `scripts\jobs.cmd`; по расписанию каждые 15 минут —
  `schtasks /create /tn "Sovga run_jobs" /sc minute /mo 15 /tr "\"C:\путь\к\проекту\scripts\jobs.cmd\""`.
- Разработка витрины с мгновенным обновлением: в `frontend` — `npm run dev` вместо окна витрины.

## Настройки

- `backend\.env` — по образцу `backend\.env.example`: база, ключи Payme / Click, коды входа, Telegram-бот, лимиты, срок возврата.
- `frontend\.env.local` — по образцу `frontend\.env.example`: адреса API и витрины.
- Секреты — только в этих файлах; в git они не попадают.

## Проверки

```
cd backend
.venv\Scripts\python.exe -m pytest            # бэкенд
cd ..\frontend
npm test                                       # фронтенд
npx tsc --noEmit
npm run lint
```

Сквозная проверка в браузере (`e2e\storefront_check.py`, нужен `pip install playwright` и `playwright install chromium`): запустите API с переменными `DEBUG=true OTP_FIXED_CODE=000000 PAYME_MERCHANT_ID=e2e PAYME_KEY=e2e-payme-key TELEGRAM_BOT_TOKEN=e2e TELEGRAM_BOT_USERNAME=sovga_e2e_bot`, витрину (`npm start`) и выполните `python e2e\storefront_check.py`.

## Боевой запуск

Пошагово — в [docs/deploy.md](docs/deploy.md): сервер Ubuntu в Узбекистане, PostgreSQL, HTTPS, службы, расписание, копии базы, настройки кабинетов Payme и Click.
