from rest_framework.permissions import BasePermission
from users.enums import UserRole


class HasTenant(BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superadmin:
            return False

        return request.tenant is not None


class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role == UserRole.ADMIN


class IsOwnerOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            if hasattr(obj, "tenant") and obj.tenant != request.tenant:
                return False
            return True

        return obj.user == request.user


class CanViewRecipe(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return obj.tenant == request.tenant

        if obj.sharing_status == "PUBLIC" and obj.tenant == request.tenant:
            return True

        return obj.user == request.user
