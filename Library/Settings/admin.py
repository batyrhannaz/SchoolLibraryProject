# Settings/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Роль в библиотеке", {"fields": ("role", "phone")}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_repr")
    list_filter = ("action",)
    search_fields = ("target_repr", "actor__username")
    readonly_fields = ("actor", "action", "target_repr", "created_at")

    def has_add_permission(self, request):
        return False  # журнал создаётся только кодом, вручную добавлять нельзя