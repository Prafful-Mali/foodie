from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.enums import UserRole


class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsOwnerOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.user.role == UserRole.ADMIN:
            return True

        return obj.user == request.user
