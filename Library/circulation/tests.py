# circulation/tests.py
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Author, Book
from .models import Loan, Reservation

User = get_user_model()


class LoanLimitTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(full_name="Тестов Тест")
        self.book = Book.objects.create(
            title="Тестовая книга", author=self.author, year=2020,
            total_copies=1, available_copies=1,
        )
        self.student = User.objects.create_user(
            username="student1", password="pass12345", role=User.Role.STUDENT
        )
        self.librarian = User.objects.create_user(
            username="lib1", password="pass12345", role=User.Role.LIBRARIAN
        )
        self.client = APIClient()

    def test_student_loan_days_is_14(self):
        loan = Loan.objects.create(user=self.student, book=self.book)
        expected_due = timezone.now().date() + timedelta(days=14)
        self.assertEqual(loan.due_date, expected_due)

    def test_teacher_loan_days_is_30(self):
        teacher = User.objects.create_user(
            username="teacher1", password="pass12345", role=User.Role.TEACHER
        )
        book2 = Book.objects.create(
            title="Вторая книга", author=self.author, year=2021,
            total_copies=1, available_copies=1,
        )
        loan = Loan.objects.create(user=teacher, book=book2)
        expected_due = timezone.now().date() + timedelta(days=30)
        self.assertEqual(loan.due_date, expected_due)

    def test_student_cannot_exceed_loan_limit(self):
        self.client.force_authenticate(user=self.librarian)
        # берём книгу первый раз — ок
        book1 = self.book
        book2 = Book.objects.create(
            title="Книга 2", author=self.author, year=2021, total_copies=1, available_copies=1
        )
        book3 = Book.objects.create(
            title="Книга 3", author=self.author, year=2022, total_copies=1, available_copies=1
        )
        Loan.objects.create(user=self.student, book=book1)
        Loan.objects.create(user=self.student, book=book2)
        # третья книга — лимит студента 2, должно быть отклонено через API
        response = self.client.post(
            "/api/circulation/loans/",
            {"user": self.student.id, "book": book3.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_fine_calculated_on_late_return(self):
        loan = Loan.objects.create(user=self.student, book=self.book)
        loan.due_date = timezone.now().date() - timedelta(days=5)
        loan.save(update_fields=["due_date"])
        loan.mark_returned()
        self.assertEqual(loan.fine_amount, 5 * Loan.FINE_PER_DAY)

    def test_no_fine_on_time_return(self):
        loan = Loan.objects.create(user=self.student, book=self.book)
        loan.mark_returned()
        self.assertEqual(loan.fine_amount, 0)


class ReservationQueueTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(full_name="Тестов Тест")
        self.book = Book.objects.create(
            title="Редкая книга", author=self.author, year=2020,
            total_copies=1, available_copies=0,  # уже разобрана
        )
        self.student1 = User.objects.create_user(
            username="student1", password="pass12345", role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            username="student2", password="pass12345", role=User.Role.STUDENT
        )

    def test_next_in_queue_gets_notified_on_return(self):
        loan = Loan.objects.create(user=self.student1, book=self.book)
        reservation = Reservation.objects.create(user=self.student2, book=self.book)

        self.assertEqual(reservation.status, Reservation.Status.WAITING)

        loan.mark_returned()
        reservation.refresh_from_db()

        self.assertEqual(reservation.status, Reservation.Status.READY)
        self.assertIsNotNone(reservation.ready_until)

    def test_queue_position(self):
        Reservation.objects.create(user=self.student1, book=self.book)
        second = Reservation.objects.create(user=self.student2, book=self.book)
        self.assertEqual(second.queue_position, 1)