from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (request.user.role == "ADMIN" or request.user.is_superadmin)
            and request.user.is_active
        )


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "ADMIN":
            return True
        return obj == request.user


class CanDeleteUser(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return obj.role == "ADMIN"

        if request.user.role == "ADMIN":
            return (
                obj != request.user
                and obj.tenant_id == request.tenant.id
                and obj.role == "USER"
            )
        return obj == request.user
