"""Тексты бота. Покупателю — на его языке; когда язык неизвестен — на двух сразу. Без разметки."""

STATUS = {
    "ru": {
        "sourcing": "Проверяем наличие у поставщика",
        "confirmed": "Ждёт оплаты",
        "awaiting_payment": "Ждём поступления оплаты",
        "paid": "Оплачен",
        "installment_pending": "Оформляется рассрочка",
        "signed": "Рассрочка оформлена",
        "cod": "Оплата при получении",
        "picking": "Собираем заказ",
        "handed_to_carrier": "Передан курьеру",
        "delivered": "Доставлен",
        "completed": "Завершён",
        "cancelled": "Отменён",
        "return_requested": "Оформляется возврат",
        "inspected": "Возврат проверен",
        "refunded": "Деньги возвращены",
    },
    "uz": {
        "sourcing": "Yetkazib beruvchida mavjudligini tekshiryapmiz",
        "confirmed": "Toʻlov kutilmoqda",
        "awaiting_payment": "Toʻlov tushishini kutyapmiz",
        "paid": "Toʻlangan",
        "installment_pending": "Muddatli toʻlov rasmiylashtirilmoqda",
        "signed": "Muddatli toʻlov rasmiylashtirildi",
        "cod": "Qabul qilishda toʻlov",
        "picking": "Buyurtma yigʻilmoqda",
        "handed_to_carrier": "Kuryerga topshirildi",
        "delivered": "Yetkazildi",
        "completed": "Yakunlandi",
        "cancelled": "Bekor qilindi",
        "return_requested": "Qaytarish rasmiylashtirilmoqda",
        "inspected": "Qaytarish tekshirildi",
        "refunded": "Pul qaytarildi",
    },
}

CUSTOMER = {
    "ru": {
        "linked": "Готово! Сюда будут приходить статусы ваших заказов.\n/orders — мои заказы, /stop — не присылать.",
        "unlinked": "Больше не присылаем статусы. Подключиться снова — кнопка «Получать статусы в Telegram» на странице заказа.",
        "no_orders": "Заказов пока нет.",
        "orders": "Ваши последние заказы:",
        "order_line": "{number} — {status} — {total} сум",
        "status": "Заказ {number}: {status}",
        "pay_now": "Товар в наличии — оплатите в течение 30 минут, пока цена зафиксирована.",
        "paid": "Спасибо! Оплата получена, собираем заказ.",
        "refund": "Если оплата уже прошла, деньги вернутся на карту.",
        "reason": "Причина: {note}",
    },
    "uz": {
        "linked": "Tayyor! Buyurtmalaringiz holati shu yerga keladi.\n/orders — buyurtmalarim, /stop — yubormaslik.",
        "unlinked": "Endi holatlarni yubormaymiz. Qayta ulanish — buyurtma sahifasidagi «Holatlarni Telegramda olish» tugmasi.",
        "no_orders": "Hozircha buyurtmalar yoʻq.",
        "orders": "Soʻnggi buyurtmalaringiz:",
        "order_line": "{number} — {status} — {total} soʻm",
        "status": "{number}-buyurtma: {status}",
        "pay_now": "Mahsulot bor — narx qotirilgan 30 daqiqa ichida toʻlang.",
        "paid": "Rahmat! Toʻlov qabul qilindi, buyurtmani yigʻyapmiz.",
        "refund": "Agar toʻlov oʻtgan boʻlsa, pul kartangizga qaytariladi.",
        "reason": "",
    },
}

HELP = (
    "Бот магазина Sovgʻa.\n/orders — мои заказы\n/stop — не присылать статусы\n/id — номер этого чата\n\n"
    "Sovgʻa doʻkoni boti.\n/orders — buyurtmalarim\n/stop — holatlarni yubormaslik\n/id — chat raqami"
)
BAD_LINK = (
    "Ссылка устарела или уже использована — откройте новую на странице заказа.\n"
    "Havola eskirgan yoki ishlatilgan — buyurtma sahifasidan yangisini oching."
)
NOT_LINKED = (
    "Этот чат не привязан к покупателю: откройте страницу заказа на сайте и нажмите «Получать статусы в Telegram».\n"
    "Bu chat xaridorga bogʻlanmagan: saytdagi buyurtma sahifasida «Holatlarni Telegramda olish» tugmasini bosing."
)
FAILED = "Не получилось, попробуйте ещё раз.\nUddalab boʻlmadi, qayta urinib koʻring."
CHAT_ID = "Номер этого чата: {chat_id}\nChat raqami: {chat_id}"
SUPPLIER_LINKED = "Готово, {name}! Сюда будут приходить заказы на подтверждение наличия."


def for_language(language: str) -> dict[str, str]:
    return CUSTOMER.get(language, CUSTOMER["ru"])


def status_label(language: str, status: str) -> str:
    return STATUS.get(language, STATUS["ru"]).get(status, status)


def money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")
