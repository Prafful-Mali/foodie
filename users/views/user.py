import logging
from django.shortcuts import get_object_or_404
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
    hard_delete_user,
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
        if request.user.is_superadmin:
            return User.objects.filter(role=UserRole.ADMIN)
        elif request.user.role == UserRole.ADMIN:
            return User.objects.filter(tenant=request.user.tenant)
        return User.objects.filter(id=request.user.id, is_active=True)

    def list(self, request):
        users = self.get_queryset(request)

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

        logger.info(f"Admin created user: {user.email}, tenant: {user.tenant_id}, by: {request.user.id}")

        return Response(
            {
                "message": "User created successfully. An email has been sent to them to set their password."
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        if request.user.role == UserRole.ADMIN or request.user.is_superadmin:
            user = get_object_or_404(User, pk=pk)
        else:
            user = get_object_or_404(User, pk=pk, is_active=True)

        self.check_object_permissions(request, user)

        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        queryset = self.get_queryset(request)
        user = get_object_or_404(queryset, pk=pk)

        is_active = request.data.get("is_active")
        if is_active is not None:
            if str(is_active).lower() == "true":
                if user.is_active:
                    return Response(
                        {"errors": {"detail": "User is already active."}},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                user.is_active = True
                user.deleted_at = None
                user.save()
                logger.info(f"User reactivated: {user.id} by: {request.user.id}")
            else:
                raise ValidationError(
                    {"detail": "To restore a user, set is_active=true."}
                )

        serializer = UserSerializer(
            user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        self.check_object_permissions(request, user)

        if not user.is_active:
            return Response(
                {"errors": {"detail": "User is already deleted."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        user.is_active = False
        user.deleted_at = now
        user.deleted_by = request.user

        if request.user.role == UserRole.ADMIN:
            eta = now + timedelta(days=90)
        else:
            user.is_email_verified = False
            eta = now + timedelta(days=7)

        user.save()
        logger.info(f"User deactivated: {user.id} by: {request.user.id}, scheduled for hard delete in {eta - now}")

        hard_delete_user.apply_async(
            args=[str(user.id)],
            eta=eta,
        )

        Recipe.objects.filter(user=user, is_active=True).update(
            is_active=False,
            deleted_at=now,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
