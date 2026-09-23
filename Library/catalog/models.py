from django.db import models


class Author(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО автора")

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Категория")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="books", verbose_name="Автор"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="books", verbose_name="Категория",
    )
    year = models.PositiveIntegerField(verbose_name="Год издания")
    isbn = models.CharField(max_length=20, blank=True, verbose_name="ISBN")
    description = models.TextField(blank=True, verbose_name="Описание")
    cover = models.ImageField(upload_to="covers/", blank=True, null=True, verbose_name="Обложка")

    total_copies = models.PositiveIntegerField(default=1, verbose_name="Всего экземпляров")
    available_copies = models.PositiveIntegerField(default=1, verbose_name="Доступно")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def is_available(self):
        return self.available_copies > 0