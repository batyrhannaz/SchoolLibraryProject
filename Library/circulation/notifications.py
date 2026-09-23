from django.core.mail import send_mail


def notify_reservation_ready(reservation):
    if not reservation.user.email:
        return
    send_mail(
        subject="Ваша книга готова к выдаче",
        message=(
            f"Здравствуйте, {reservation.user.get_full_name() or reservation.user.username}!\n\n"
            f"Книга «{reservation.book.title}» теперь доступна.\n"
            f"Заберите её в библиотеке до {reservation.ready_until}.\n"
        ),
        from_email=None,
        recipient_list=[reservation.user.email],
        fail_silently=True,
    )


def notify_loan_overdue(loan):
    if not loan.user.email:
        return
    send_mail(
        subject="Просрочен возврат книги",
        message=(
            f"Здравствуйте, {loan.user.get_full_name() or loan.user.username}!\n\n"
            f"Срок возврата книги «{loan.book.title}» истёк {loan.due_date}.\n"
            f"Пожалуйста, верните книгу как можно скорее, чтобы не увеличивать штраф.\n"
        ),
        from_email=None,
        recipient_list=[loan.user.email],
        fail_silently=True,
    )