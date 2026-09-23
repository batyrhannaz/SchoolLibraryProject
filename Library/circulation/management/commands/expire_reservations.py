# circulation/management/commands/expire_reservations.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from circulation.models import Reservation


class Command(BaseCommand):
    help = "Отменяет брони, которые не забрали в течение отведённого срока (ready_until)"

    def handle(self, *args, **options):
        today = timezone.now().date()
        expired = Reservation.objects.filter(
            status=Reservation.Status.READY,
            ready_until__lt=today,
        )
        count = 0
        for reservation in expired:
            reservation.status = Reservation.Status.CANCELLED
            reservation.save(update_fields=["status"])
            count += 1

            # передаём книгу следующему в очереди
            next_reservation = (
                Reservation.objects.filter(
                    book=reservation.book, status=Reservation.Status.WAITING
                )
                .order_by("created_at")
                .first()
            )
            if next_reservation:
                next_reservation.mark_ready()

        self.stdout.write(self.style.SUCCESS(f"Отменено просроченных броней: {count}"))