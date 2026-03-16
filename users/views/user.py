import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from recipes.models import Recipe
from ..serializers import (
    UserSerializer,
    CreateUserSerializer,
)
from common.pagination import DefaultPagination
from ..permissions import IsAdmin, IsOwnerOrAdmin, CanDeleteUser
from ..models import User
from ..tasks import (
    deactivate_user_resources,
    restore_user_resources,
    send_setup_password_email,
)
from common.enums import UserRole

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ["list", "partial_update", "create"]:
            permission_classes = [IsAuthenticated, IsAdmin]
        elif self.action in ["retrieve"]:
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action in ["destroy"]:
            permission_classes = [IsAuthenticated, CanDeleteUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        base_qs = User.objects.select_related("tenant")
        if request.user.is_superadmin:
            return base_qs.filter(role=UserRole.ADMIN)
        elif request.user.role == UserRole.ADMIN:
            return base_qs.filter(tenant=request.user.tenant)
        return base_qs.filter(id=request.user.id, is_active=True)

    def list(self, request):
        users = (
            self.get_queryset(request)
            .only(
                "id",
                "username",
                "email",
                "is_email_verified",
                "first_name",
                "last_name",
                "role",
                "tenant__id",
                "tenant__name",
                "is_active",
                "created_at",
                "updated_at",
                "deleted_at",
            )
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        if status_param == "active":
            users = users.filter(is_active=True)
        elif status_param == "deleted":
            users = users.filter(is_active=False)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(
            paginated_qs, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        serializer = CreateUserSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        base_url = request.build_absolute_uri("/")[:-1]
        send_setup_password_email.delay(user.email, base_url)

        logger.info(
            f"Admin created user: {user.email}, tenant: {user.tenant_id}, by: {request.user.id}"
        )

        return Response(
            {
                "message": "User created successfully. An email has been sent to them to set their password."
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        base_qs = User.objects.select_related("tenant")
        if request.user.role == UserRole.ADMIN or request.user.is_superadmin:
            user = get_object_or_404(base_qs, pk=pk)
        else:
            user = get_object_or_404(base_qs, pk=pk, is_active=True)

        self.check_object_permissions(request, user)

        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        queryset = self.get_queryset(request)
        user = get_object_or_404(queryset, pk=pk)

        is_restoring = not user.is_active and request.data.get("is_active") is True

        deleted_at_timestamp = None
        if is_restoring:
            if user.is_active:
                return Response(
                    {"errors": {"detail": "User is already active."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if user.deleted_at:
                deleted_at_timestamp = user.deleted_at.isoformat()

        serializer = UserSerializer(
            user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        if is_restoring:
            user.is_active = True
            user.deleted_at = None
            user.save()

        serializer.save()

        if is_restoring and deleted_at_timestamp:
            restore_user_resources.delay(str(user.id), deleted_at_timestamp)
            logger.info(f"User reactivated: {user.id} by: {request.user.id}")

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = get_object_or_404(User, pk=pk, is_active=True)
        self.check_object_permissions(request, user)

        deleted_at = timezone.now()
        user.is_active = False
        user.deleted_at = deleted_at
        user.deleted_by = request.user

        if request.user.role != UserRole.ADMIN:
            user.is_email_verified = False

        user.save()

        deactivate_user_resources.delay(str(user.id), deleted_at.isoformat())

        logger.info(f"User deactivated: {user.id} by: {request.user.id}")

        return Response(status=status.HTTP_204_NO_CONTENT)
