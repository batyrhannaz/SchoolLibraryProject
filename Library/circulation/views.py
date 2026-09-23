# circulation/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from rest_framework.views import APIView
from catalog.models import Book
from .models import *
from .permissions import IsLibrarian, IsOwnerOrLibrarian
from .serializers import *
from django.utils import timezone

from Settings.audit import log_action
from Settings.models import AuditLog


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "user", "book"]

    def get_permissions(self):
        if self.action in ("create", "return_book", "pay_fine"):
            return [permissions.IsAuthenticated(), IsLibrarian()]
        return [permissions.IsAuthenticated(), IsOwnerOrLibrarian()]

    def get_queryset(self):
        user = self.request.user
        qs = Loan.objects.select_related("user", "book")
        if getattr(user, "is_librarian", False):
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        loan = serializer.save()
        log_action(self.request.user, AuditLog.Action.ISSUE_BOOK, loan)

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        loan = self.get_object()
        if loan.status == Loan.Status.RETURNED:
            return Response({"detail": "Книга уже возвращена."}, status=400)
        loan.mark_returned()
        log_action(request.user, AuditLog.Action.RETURN_BOOK, loan)
        return Response(LoanSerializer(loan).data)

    @action(detail=True, methods=["post"], url_path="extend")
    def extend_loan(self, request, pk=None):
        loan = self.get_object()
        try:
            loan.extend()
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        log_action(request.user, AuditLog.Action.EXTEND_LOAN, loan)
        return Response(LoanSerializer(loan).data)

    @action(detail=True, methods=["post"], url_path="pay-fine")
    def pay_fine(self, request, pk=None):
        loan = self.get_object()
        if loan.fine_amount == 0:
            return Response({"detail": "У этой выдачи нет штрафа."}, status=400)
        loan.fine_paid = True
        loan.save(update_fields=["fine_paid"])
        log_action(request.user, AuditLog.Action.PAY_FINE, loan)
        return Response(LoanSerializer(loan).data)


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "user", "book"]

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsOwnerOrLibrarian()]

    def get_queryset(self):
        user = self.request.user
        qs = Reservation.objects.select_related("user", "book")
        if getattr(user, "is_librarian", False):
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        reservation = serializer.save(user=self.request.user)
        log_action(self.request.user, AuditLog.Action.CREATE_RESERVATION, reservation)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status in (Reservation.Status.CANCELLED, Reservation.Status.FULFILLED):
            return Response({"detail": "Бронь уже неактивна."}, status=400)
        reservation.status = Reservation.Status.CANCELLED
        reservation.save(update_fields=["status"])
        log_action(request.user, AuditLog.Action.CANCEL_RESERVATION, reservation)
        return Response(ReservationSerializer(reservation).data)


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsLibrarian]

    def get(self, request):
        today = timezone.now().date()
        return Response({
            "total_books": Book.objects.count(),
            "books_available": Book.objects.filter(available_copies__gt=0).count(),
            "active_loans": Loan.objects.filter(status=Loan.Status.ACTIVE).count(),
            "overdue_loans": Loan.objects.filter(
                status=Loan.Status.ACTIVE, due_date__lt=today
            ).count(),
            "waiting_reservations": Reservation.objects.filter(
                status=Reservation.Status.WAITING
            ).count(),
            "top_books": list(
                Book.objects.annotate(loan_count=Count("loans"))
                .order_by("-loan_count")[:5]
                .values("id", "title", "loan_count")
            ),
        })