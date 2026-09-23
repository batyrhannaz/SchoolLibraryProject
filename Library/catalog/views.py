# catalog/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Author, Book, Category
from .permissions import IsLibrarianOrReadOnly
from .serializers import AuthorSerializer, BookSerializer, CategorySerializer

from Settings.audit import log_action
from Settings.models import AuditLog


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsLibrarianOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name"]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsLibrarianOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("author", "category").all()
    serializer_class = BookSerializer
    permission_classes = [IsLibrarianOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["author", "category", "year"]
    search_fields = ["title", "author__full_name", "isbn"]
    ordering_fields = ["title", "year", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        available = self.request.query_params.get("available")
        if available == "true":
            qs = qs.filter(available_copies__gt=0)
        elif available == "false":
            qs = qs.filter(available_copies=0)
        return qs

    def perform_create(self, serializer):
        book = serializer.save()
        log_action(self.request.user, AuditLog.Action.CREATE_BOOK, book)

    def perform_update(self, serializer):
        book = serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE_BOOK, book)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.Action.DELETE_BOOK, instance)
        instance.delete()