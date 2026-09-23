from .models import AuditLog


def log_action(user, action, target):
    AuditLog.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        target_repr=str(target),
    )