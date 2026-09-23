from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Ученик"
        TEACHER = "teacher", "Учитель"
        LIBRARIAN = "librarian", "Библиотекарь"
        ADMIN = "admin", "Администратор"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT, verbose_name="Роль"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, verbose_name="Аватар"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_librarian(self):
        return self.role in (self.Role.LIBRARIAN, self.Role.ADMIN) or self.is_superuser

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class AuditLog(models.Model):
    class Action(models.TextChoices):
        ISSUE_BOOK = "issue_book", "Выдача книги"
        RETURN_BOOK = "return_book", "Возврат книги"
        EXTEND_LOAN = "extend_loan", "Продление выдачи"
        PAY_FINE = "pay_fine", "Оплата штрафа"
        CREATE_RESERVATION = "create_reservation", "Бронирование"
        CANCEL_RESERVATION = "cancel_reservation", "Отмена брони"
        CREATE_BOOK = "create_book", "Добавление книги"
        UPDATE_BOOK = "update_book", "Изменение книги"
        DELETE_BOOK = "delete_book", "Удаление книги"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="audit_actions", verbose_name="Кто выполнил",
    )
    action = models.CharField(max_length=30, choices=Action.choices, verbose_name="Действие")
    target_repr = models.CharField(max_length=255, verbose_name="Объект")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")

    class Meta:
        verbose_name = "Запись журнала"
        verbose_name_plural = "Журнал действий"
        ordering = ["-created_at"]

    def __str__(self):
        who = self.actor.username if self.actor else "система"
        return f"{who}: {self.get_action_display()} — {self.target_repr}"