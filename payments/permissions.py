from rest_framework.permissions import BasePermission
from users.enums import UserRole


class IsTenantAdmin(BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return getattr(request.user, "role", None) == UserRole.ADMIN
