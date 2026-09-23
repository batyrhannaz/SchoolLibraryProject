from django.contrib import admin

from .models import Author, Book, Category


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("full_name",)
    search_fields = ("full_name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "year", "total_copies", "available_copies")
    list_filter = ("category", "year")
    search_fields = ("title", "author__full_name", "isbn")