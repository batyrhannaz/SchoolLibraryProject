# circulation/models.py
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Loan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "На руках"
        RETURNED = "returned", "Возвращена"
        OVERDUE = "overdue", "Просрочена"

    # срок выдачи (в днях) и лимит книг одновременно — по ролям
    LOAN_DAYS_BY_ROLE = {
        "student": 14,
        "teacher": 30,
        "librarian": 30,
        "admin": 30,
    }
    MAX_ACTIVE_LOANS_BY_ROLE = {
        "student": 2,
        "teacher": 5,
        "librarian": 10,
        "admin": 10,
    }
    FINE_PER_DAY = 10  # штраф за каждый день просрочки, в вашей валюте

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="loans", verbose_name="Читатель",
    )
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.CASCADE,
        related_name="loans", verbose_name="Книга",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="issued_loans", verbose_name="Выдал библиотекарь",
    )

    issue_date = models.DateField(auto_now_add=True, verbose_name="Дата выдачи")
    due_date = models.DateField(verbose_name="Срок возврата")
    return_date = models.DateField(null=True, blank=True, verbose_name="Дата возврата")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="Статус"
    )
    fine_amount = models.PositiveIntegerField(default=0, verbose_name="Штраф")
    fine_paid = models.BooleanField(default=False, verbose_name="Штраф оплачен")

    MAX_EXTENSIONS = 1
    extensions_used = models.PositiveIntegerField(default=0, verbose_name="Использовано продлений")

    class Meta:
        verbose_name = "Выдача"
        verbose_name_plural = "Выдачи"
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.book} → {self.user} ({self.get_status_display()})"

    @classmethod
    def loan_days_for(cls, user):
        return cls.LOAN_DAYS_BY_ROLE.get(getattr(user, "role", None), 14)

    @classmethod
    def max_active_loans_for(cls, user):
        return cls.MAX_ACTIVE_LOANS_BY_ROLE.get(getattr(user, "role", None), 2)

    def save(self, *args, **kwargs):
        if not self.due_date:
            days = self.loan_days_for(self.user)
            self.due_date = timezone.now().date() + timedelta(days=days)
        super().save(*args, **kwargs)

    def mark_returned(self):
        today = timezone.now().date()
        self.return_date = today
        self.status = self.Status.RETURNED
        if today > self.due_date:
            overdue_days = (today - self.due_date).days
            self.fine_amount = overdue_days * self.FINE_PER_DAY
        self.save(update_fields=["return_date", "status", "fine_amount"])
        self.book.available_copies += 1
        self.book.save(update_fields=["available_copies"])

        # если на эту книгу есть очередь — уведомляем следующего
        next_reservation = (
            Reservation.objects.filter(book=self.book, status=Reservation.Status.WAITING)
            .order_by("created_at")
            .first()
        )
        if next_reservation:
            next_reservation.mark_ready()

    def can_extend(self):
        if self.status != self.Status.ACTIVE:
            return False, "Можно продлить только активную выдачу."
        if self.extensions_used >= self.MAX_EXTENSIONS:
            return False, "Лимит продлений уже исчерпан."
        if self.is_overdue:
            return False, "Нельзя продлить просроченную книгу — сначала верните её."
        # если книгу кто-то ждёт в очереди — продлевать нельзя
        has_waiting = Reservation.objects.filter(
            book=self.book, status=Reservation.Status.WAITING
        ).exists()
        if has_waiting:
            return False, "На эту книгу есть очередь — продление недоступно."
        return True, ""

    def extend(self):
        ok, reason = self.can_extend()
        if not ok:
            raise ValueError(reason)
        days = self.loan_days_for(self.user)
        self.due_date = self.due_date + timedelta(days=days)
        self.extensions_used += 1
        self.save(update_fields=["due_date", "extensions_used"])

    @property
    def is_overdue(self):
        return self.status == self.Status.ACTIVE and timezone.now().date() > self.due_date

    @property
    def current_fine(self):
        if self.status == self.Status.RETURNED:
            return self.fine_amount
        if self.is_overdue:
            overdue_days = (timezone.now().date() - self.due_date).days
            return overdue_days * self.FINE_PER_DAY
        return 0

class Reservation(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "В очереди"
        READY = "ready", "Готова к выдаче"
        CANCELLED = "cancelled", "Отменена"
        FULFILLED = "fulfilled", "Выполнена"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="reservations", verbose_name="Читатель",
    )
    book = models.ForeignKey(
        "catalog.Book", on_delete=models.CASCADE,
        related_name="reservations", verbose_name="Книга",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата бронирования")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING, verbose_name="Статус"
    )
    ready_until = models.DateField(
        null=True, blank=True,
        verbose_name="Забрать до",
        help_text="Срок, до которого нужно забрать книгу, иначе бронь снимается",
    )

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ["created_at"]  # чем раньше встал в очередь, тем выше

    def __str__(self):
        return f"{self.book} — {self.user} ({self.get_status_display()})"

    @property
    def queue_position(self):
        """Позиция в очереди среди тех, кто ещё ждёт (без учёта самого себя = 0)."""
        if self.status != self.Status.WAITING:
            return 0
        return Reservation.objects.filter(
            book=self.book, status=self.Status.WAITING, created_at__lt=self.created_at
        ).count()

    def mark_ready(self, days_to_pickup=3):
        self.status = self.Status.READY
        self.ready_until = timezone.now().date() + timedelta(days=days_to_pickup)
        self.save(update_fields=["status", "ready_until"])
        from .notifications import notify_reservation_ready
        notify_reservation_ready(self)