# circulation/management/commands/mark_overdue.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from circulation.models import Loan
from circulation.notifications import notify_loan_overdue


class Command(BaseCommand):
    help = "Помечает просроченные выдачи статусом OVERDUE и уведомляет читателей"

    def handle(self, *args, **options):
        today = timezone.now().date()
        overdue_loans = Loan.objects.filter(status=Loan.Status.ACTIVE, due_date__lt=today)
        count = 0
        for loan in overdue_loans:
            loan.status = Loan.Status.OVERDUE
            loan.save(update_fields=["status"])
            notify_loan_overdue(loan)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Обновлено просроченных выдач: {count}"))