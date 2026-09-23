# circulation/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, LoanViewSet, ReservationViewSet

router = DefaultRouter()
router.register("loans", LoanViewSet, basename="loan")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = router.urls + [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]