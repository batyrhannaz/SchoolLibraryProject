from rest_framework import permissions


class IsLibrarian(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_librarian", False)
        )


class IsOwnerOrLibrarian(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_librarian", False):
            return True
        return obj.user_id == request.user.id