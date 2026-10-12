from django.db import models


class OutboxEvent(models.Model):
    """Событие пишется в той же транзакции, что и изменение данных, а доставляется потом — с повторами."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ждёт доставки"
        DONE = "done", "Доставлено"
        FAILED = "failed", "Не удалось"

    type = models.CharField(max_length=64, db_index=True, verbose_name="тип")
    payload = models.JSONField(default=dict, verbose_name="данные")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True, verbose_name="статус"
    )
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="попыток")
    next_attempt_at = models.DateTimeField(db_index=True, verbose_name="следующая попытка")
    last_error = models.TextField(blank=True, verbose_name="последняя ошибка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="создан")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="обработано")

    class Meta:
        verbose_name = "событие"
        verbose_name_plural = "очередь событий"
        ordering = ["-pk"]

    def __str__(self) -> str:
        return f"{self.type} #{self.pk}"
