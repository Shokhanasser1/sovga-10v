# План 4b. Оплата Payme и Click — план реализации

> Выполняется по задачам, каждая через TDD: тест → падает → код → проходит → коммит.

**Goal:** Покупатель оплачивает подтверждённый заказ через Payme или Click; колбэки провайдеров переводят заказ в «Оплачен» строго по машине состояний, идемпотентно и с проверкой подлинности; Payme получает данные для фискального чека (ИКПУ, код упаковки).

**Architecture:** Приложение `payments`: модель `Payment` (одна транзакция провайдера), общий сервис переходов заказа при оплате, адаптеры протоколов `payme.py` (JSON-RPC Merchant API) и `click.py` (SHOP API: Prepare/Complete), ссылки на оплату. Провайдер вызывает наш сервер напрямую — эндпоинты без CSRF и без лимита частоты, но с проверкой Basic-аутентификации (Payme) и MD5-подписи (Click).

**Спецификация:** раздел 5 («Когда берём оплату»), раздел 4 (вебхуки: подпись, идемпотентность).

## Global Constraints

Все ограничения Планов 1–4a действуют. Дополнительно:
- Суммы: Payme — в тийинах (сум × 100, целое), Click — в сумах; сравниваются с `Order.total_uzs` точно.
- Каждая транзакция провайдера уникальна по `(provider, external_id)`; повторный вызов возвращает тот же результат.
- Одновременно у заказа может быть только одна незавершённая транзакция.
- Окно оплаты после начала транзакции — 12 часов (тайм-аут Payme); резервы продлеваются на это окно; после оплаты — ещё на 7 дней до сборки.
- Секреты (`PAYME_KEY`, `CLICK_SECRET_KEY`) — только из окружения; сравнение — `hmac.compare_digest`.
- Без настроек провайдера ссылка на оплату отвечает 503 «Оплата временно недоступна».
- Форматы запросов — по документации Payme Merchant API и Click SHOP API; перед запуском проверить в песочницах провайдеров.

## Задачи

### Task 1. Платежи и переходы заказа (`payments`)
- `Payment(order, provider, external_id, amount_uzs, state, provider_state, created_at, performed_at, cancelled_at, cancel_reason, raw)`.
- `services.py`: `start_payment`, `confirm_payment`, `fail_payment`, `refund_payment` — через `orders.services.transition` с проверкой под блокировкой; `order.paid` в outbox.
- Тесты: CONFIRMED → AWAITING_PAYMENT с продлением резервов; оплата → PAID; неудача → снова CONFIRMED; возврат после оплаты → CANCELLED; после передачи курьеру возврат запрещён.

### Task 2. Payme Merchant API
- `POST /api/v1/payments/payme/`: Basic `Paycom:<PAYME_KEY>`, JSON-RPC 2.0; методы `CheckPerformTransaction` (с `detail` для фискального чека), `CreateTransaction`, `PerformTransaction`, `CancelTransaction`, `CheckTransaction`, `GetStatement`.
- Тесты: неверная авторизация (−32504), неизвестный метод (−32601), неверная сумма (−31001), нет заказа (−31050), заказ нельзя оплатить (−31051), чужая активная транзакция (−31052), тайм-аут 12 ч (−31008, причина 4), повторы, отмена до и после проведения, −31007, выписка.

### Task 3. Click SHOP API
- `POST /api/v1/payments/click/prepare/` и `/complete/` (form-urlencoded), подпись `md5(click_trans_id + service_id + SECRET + merchant_trans_id [+ merchant_prepare_id] + amount + action + sign_time)`.
- Тесты: успех, неверная подпись (−1), неверная сумма (−2), неверный action (−3), уже оплачен (−4), нет заказа (−5), нет транзакции (−6), ошибка оплаты со стороны Click → отмена (−9), повторы.

### Task 4. Ссылка на оплату, просрочка, уведомление
- `POST /api/v1/orders/<number>/pay/ {provider}` → `{url}`; Payme: `checkout.paycom.uz/<base64(m=…;ac.order_id=…;a=…;c=…;l=…)>`, Click: `my.click.uz/services/pay?service_id=…&merchant_id=…&amount=…&transaction_param=…&return_url=…`.
- `expire_orders` отменяет AWAITING_PAYMENT после окна оплаты; обработчик `order.paid` → менеджерам.
- Тесты: ссылки, 503 без настроек, чужой заказ, неоплачиваемый статус.

### Task 5. Админка, витрина, сквозная проверка
- Админка платежей (только чтение). На странице заказа — кнопки «Оплатить через Payme / Click».
- e2e: оформить заказ, затем скрипт в роли Payme проводит оплату — заказ «Оплачен».
