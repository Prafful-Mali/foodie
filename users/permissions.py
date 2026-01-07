from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "ADMIN"
            and request.user.is_active
        )


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "ADMIN":
            return True
        return obj == request.user


class CanDeleteUser(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "ADMIN":
            return obj != request.user
        return obj == request.user
