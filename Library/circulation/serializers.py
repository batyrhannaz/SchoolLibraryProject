from rest_framework import serializers

from catalog.models import Book

from .models import *


class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    current_fine = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = (
            "id", "user", "user_name", "book", "book_title",
            "issued_by", "issue_date", "due_date", "return_date",
            "status", "is_overdue", "fine_amount", "fine_paid", "current_fine",
            "extensions_used",
        )
        read_only_fields = ("issue_date", "return_date", "status", "issued_by", "fine_amount")

    def validate_book(self, book):
        if book.available_copies < 1:
            raise serializers.ValidationError("Все экземпляры этой книги уже выданы.")
        return book

    def validate(self, attrs):
        user = attrs["user"]

        active_count = Loan.objects.filter(user=user, status=Loan.Status.ACTIVE).count()
        limit = Loan.max_active_loans_for(user)
        if active_count >= limit:
            raise serializers.ValidationError(
                f"У читателя уже {active_count} книг на руках (максимум {limit} для его роли)."
            )

        unpaid_fines = Loan.objects.filter(
            user=user, fine_amount__gt=0, fine_paid=False
        ).exclude(status=Loan.Status.ACTIVE).exists()
        if unpaid_fines:
            raise serializers.ValidationError(
                "У читателя есть непогашенный штраф. Сначала оплатите штраф, потом можно брать новые книги."
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        book: Book = validated_data["book"]

        loan = Loan.objects.create(
            user=validated_data["user"],
            book=book,
            issued_by=request.user,
        )
        book.available_copies -= 1
        book.save(update_fields=["available_copies"])
        return loan


class ReservationSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    queue_position = serializers.IntegerField(read_only=True)

    class Meta:
        model = Reservation
        fields = (
            "id", "user", "user_name", "book", "book_title",
            "created_at", "status", "ready_until", "queue_position",
        )
        read_only_fields = ("status", "ready_until")

    def validate_book(self, book):
        if book.available_copies > 0:
            raise serializers.ValidationError(
                "Книга сейчас доступна — можно оформить выдачу напрямую, без бронирования."
            )
        return book

    def validate(self, attrs):
        user = attrs["user"]
        book = attrs["book"]
        exists = Reservation.objects.filter(
            user=user, book=book, status=Reservation.Status.WAITING
        ).exists()
        if exists:
            raise serializers.ValidationError("Вы уже в очереди на эту книгу.")
        return attrs