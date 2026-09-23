from rest_framework import serializers

from .models import Author, Book, Category


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ("id", "full_name")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class BookSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Book
        fields = (
            "id", "title", "author", "author_name", "category", "category_name",
            "year", "isbn", "description", "cover",
            "total_copies", "available_copies", "is_available", "created_at",
        )
        read_only_fields = ("available_copies",)

    def create(self, validated_data):
        validated_data["available_copies"] = validated_data.get("total_copies", 1)
        return super().create(validated_data)