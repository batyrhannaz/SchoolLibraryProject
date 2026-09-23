from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="page-index"),
    path("login/", views.LoginView.as_view(), name="page-login"),
    path("catalog/", views.CatalogView.as_view(), name="page-catalog"),
    path("loans/", views.LoansView.as_view(), name="page-loans"),
    path("admin-panel/", views.AdminPanelView.as_view(), name="page-admin-panel"),
    path("profile/", views.ProfileView.as_view(), name="page-profile"),
]