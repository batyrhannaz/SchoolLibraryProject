from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = "index.html"


class LoginView(TemplateView):
    template_name = "login.html"


class CatalogView(TemplateView):
    template_name = "catalog.html"


class LoansView(TemplateView):
    template_name = "loans.html"


class AdminPanelView(TemplateView):
    template_name = "admin_panel.html"

class ProfileView(TemplateView):
    template_name = "profile.html"