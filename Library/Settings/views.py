from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import filters
from .models import User
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from rest_framework import serializers

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.get_tokens(serializer.validated_data["user"])
        return Response(data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserSearchView(generics.ListAPIView):
    """Поиск пользователей по username — нужен библиотекарю при выдаче книги."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "first_name", "last_name"]

    def get_queryset(self):
        if not getattr(self.request.user, "is_librarian", False):
            return User.objects.none()
        return User.objects.all().order_by("username")

# Settings/views.py — добавить в конец файла

class ProfileStatsView(APIView):
    """Личная статистика читателя: сколько книг на руках, штрафы, брони, история."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from circulation.models import Loan, Reservation
        from circulation.serializers import LoanSerializer, ReservationSerializer

        user = request.user
        loans = Loan.objects.filter(user=user).select_related("book")
        active_loans = loans.filter(status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE])
        total_fines = sum(loan.current_fine for loan in active_loans)
        unpaid_returned_fines = (
            loans.filter(status=Loan.Status.RETURNED, fine_paid=False)
            .exclude(fine_amount=0)
        )
        total_fines += sum(loan.fine_amount for loan in unpaid_returned_fines)

        reservations = Reservation.objects.filter(
            user=user, status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
        ).select_related("book")

        return Response({
            "user": UserSerializer(user).data,
            "active_loans_count": active_loans.count(),
            "max_loans": Loan.max_active_loans_for(user),
            "loan_days": Loan.loan_days_for(user),
            "total_fines_owed": total_fines,
            "active_loans": LoanSerializer(active_loans, many=True).data,
            "reservations": ReservationSerializer(reservations, many=True).data,
            "loan_history_count": loans.filter(status=Loan.Status.RETURNED).count(),
        })

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True, default=None)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = ("id", "actor", "actor_name", "action", "action_display", "target_repr", "created_at")


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not getattr(self.request.user, "is_librarian", False):
            return AuditLog.objects.none()
        return AuditLog.objects.select_related("actor").all()[:200]