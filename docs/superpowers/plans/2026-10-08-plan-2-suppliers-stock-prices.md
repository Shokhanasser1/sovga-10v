# План 2. Поставщики, остатки, IMEI, цены — план реализации

> Выполняется по задачам, каждая через TDD: тест → падает → код → проходит → коммит.

**Goal:** Прайсы поставщиков загружаются и сопоставляются с SKU, свой склад ведётся поштучно по IMEI, система выбирает источник товара, резервирует его и держит актуальную цену в сумах; всё периодическое выполняет одна команда `run_jobs`.

**Architecture:** Новые приложения `sourcing` (поставщики, склады, предложения, прайсы, сопоставление, выбор источника, резервы) и `inventory` (партии, единицы с IMEI). `pricing` получает снимки цен и пересчёт. Направление зависимостей: `catalog` ← `sourcing` ← `inventory`; `catalog`, `sourcing` ← `pricing`; `core` оркестрирует команды. Без Docker, Redis и Celery (спецификация, раздел 4, решение 2026-10-08).

**Tech Stack:** как в Плане 1 + openpyxl (Excel), csv/json из стандартной библиотеки, difflib для нечёткого сопоставления.

## Global Constraints

Все ограничения Плана 1 действуют. Дополнительно:
- Никаких внешних сервисов для запуска: только Python и SQLite.
- Остаток предложения (`Offer.qty_available`) — сырой остаток источника; резервы хранятся отдельно и вычитаются при расчёте доступности.
- Прайс поставщика — полный снимок: позиции, которых нет в прайсе, получают остаток 0. При ошибке загрузки остатки не трогаются (устаревают по TTL).
- TTL свежести по умолчанию: api — 1 ч, sheet — 24 ч, file — 24 ч, telegram — 6 ч.
- Курс сдвинулся ≤ 0,5 % — цена пересчитывается по прежнему курсу (цены не дёргаются).
- Себестоимость и закупочные цены никогда не попадают в публичное API.

## Задачи

### Task 1. Поставщики, склады, предложения (`sourcing`)
- Модели: `Supplier(name, connector_type: api|sheet|file|telegram, feed_url, columns, ttl_hours, reliability 0.10–1.00, lead_time_days, payment_terms, contact, is_active)` + `effective_ttl`; `Warehouse(name, address, is_active)`; `Offer(variant, supplier | warehouse — ровно один, cost_usd, qty_available, lead_time_days, last_confirmed_at, is_active)` + `is_own`, `is_fresh(now)`.
- Тесты: ровно один источник (CheckConstraint); свежесть по TTL типа и по `ttl_hours`; свой склад всегда свежий.

### Task 2. Чтение прайсов (`sourcing/feeds.py`, без БД)
- `FeedRow(code, name, price_usd, qty, raw, error)`; `validate_columns(columns) -> list[str]`; `parse_rows(records, columns) -> list[FeedRow]`; `read_csv(text)`, `read_xlsx(file)`, `read_json(payload)`.
- Тесты: форматы цены (`1299`, `1 299,50`, `$1,299.00`, мусор), остатка (`5`, `5.0`, `10+`, `>10`, `нет`), ошибки строк, пропуск пустых строк, CSV с `;`, Excel из временного файла, JSON-список и `{"items": [...]}`.

### Task 3. Импорт прайса (`sourcing/importer.py`)
- Модели: `SupplierSkuMap(supplier, supplier_code → variant)`, `SupplierFeedRun(supplier, started_at, счётчики, error)`, `SupplierFeedRow(run, supplier_code, name, price_usd, qty, raw, status: matched|unmatched|invalid, error, variant)`.
- `import_feed(supplier, rows, now) -> SupplierFeedRun`; `upsert_offer(supplier, variant_id, price_usd, qty, confirmed_at) -> Offer`.
- Тесты: сопоставленная строка обновляет предложение; несопоставленная попадает в очередь; ошибочная — invalid; отсутствующая в прайсе позиция → остаток 0; счётчики прогона.

### Task 4. Очередь сопоставления (`sourcing/matching.py`)
- `normalize(text)`, `similarity(a, b)`, `variant_label(variant)`, `suggest_variants(name, limit=5) -> list[tuple[Variant, float]]`, `confirm_match(row, variant) -> Offer | None`.
- Тесты: нормализация «256 ГБ»/«256GB», ранжирование подсказок, подтверждение создаёт привязку и предложение со временем прогона, следующий импорт сопоставляет автоматически.

### Task 5. Выбор источника, доступность, резервы (`sourcing/routing.py`, `sourcing/reservations.py`)
- `offer_score(cost_usd, lead_time_days, reliability)` (меньше — лучше; день срока = +1 %, цена делится на надёжность); `available_qty(offer, now)`; `choose_offer(variant, qty, now) -> Offer | None` (свой склад → лучший свежий поставщик); `Availability(status: in_stock|on_order|out_of_stock, lead_time_days)`, `availability(variant, now)`.
- Модель `Reservation(offer, qty, ref, is_soft, expires_at, released_at)`; `reserve(variant, qty, ref, now, ttl=15 мин) -> Reservation | None`, `release(reservation, now)`, `release_expired(now) -> int`.
- Тесты: приоритет своего склада, баллы поставщиков, устаревшие и неактивные пропускаются, резервы уменьшают доступность, просроченные снимаются, «под заказ» для устаревшего остатка.

### Task 6. Склад по IMEI (`inventory`)
- `is_valid_imei(value)` (15 цифр, контрольная цифра Луна), `validate_imei`; модели `PurchaseBatch(supplier, received_at, note)`, `InventoryUnit(variant, warehouse, imei1, imei2, serial, uzimei_status, purchase_batch, cost_usd, status)`; `receive_unit(...)`, `sync_own_offer(variant, warehouse)`.
- Тесты: проверка IMEI, уникальность IMEI1, нужен IMEI или серийный номер, только для поштучных категорий, приёмка создаёт/обновляет своё предложение (количество и средняя себестоимость).

### Task 7. Снимки цен и пересчёт (`pricing/repricing.py`)
- Модель `PriceSnapshot(variant, price_uzs, cost_usd, rate, offer, markup_rule, computed_at)`; `current_price(variant)`, `reprice_variant(variant, rate, now)`, `reprice_all(rate, now) -> RepriceResult(changed, unpriced, missing_rule)`.
- Тесты: первая цена, без изменений — без нового снимка, малый сдвиг курса держит цену, большой — пересчитывает, смена закупки или правила — пересчитывает, нет предложения — без цены, нет правила — в отчёт.

### Task 8. Команды и `run_jobs`
- `sourcing/fetch.py`: `fetch_feed_records(supplier, http_get)`, `sync_supplier(supplier, now, http_get)`; команды `import_supplier_feeds`, `import_feed_file <supplier_id> <path>`; `core` — `run_jobs` (прайсы → курс ЦБ → цены → резервы).
- Тесты: CSV/JSON по ссылке, ошибка сети не обнуляет остатки, не заданы колонки — прогон с ошибкой, импорт Excel-файла командой, `run_jobs` выполняет все шаги и не падает без курса.

### Task 9. Админка
- Поставщики, склады, предложения, прогоны, очередь сопоставления (подсказки + выбор SKU → `confirm_match`), привязки, резервы, партии, единицы с IMEI (сохранение синхронизирует предложение), снимки цен.
- Тесты: страницы открываются; выбор SKU в очереди создаёт привязку; правка единицы обновляет остаток.

### Task 10. API цены и наличия
- `GET /api/v1/pricing/products/<slug>/` → по активным вариантам: `sku`, `price_uzs`, `availability {status, lead_time_days}`, `gift_budget_uzs`. Без себестоимости.
- Тесты: цена, наличие и бюджет подарка; черновики скрыты; нет цены → `null` и «нет в наличии»; 404 для неизвестного товара.
