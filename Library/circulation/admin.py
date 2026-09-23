from django.contrib import admin

from .models import Loan, Reservation


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "issue_date", "due_date", "status", "fine_amount")
    list_filter = ("status",)
    search_fields = ("book__title", "user__username")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "created_at", "status", "ready_until")
    list_filter = ("status",)
    search_fields = ("book__title", "user__username")