from django.db import models


class OutboxEvent(models.Model):
    """Событие пишется в той же транзакции, что и изменение данных, а доставляется потом — с повторами."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ждёт доставки"
        DONE = "done", "Доставлено"
        FAILED = "failed", "Не удалось"

    type = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(db_index=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-pk"]

    def __str__(self) -> str:
        return f"{self.type} #{self.pk}"
