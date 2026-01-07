from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from recipes.models import Recipe
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    TempPasswordEmailSerializer,
    ChangePasswordSerializer,
    UserSerializer,
)
from foodie.pagination import DefaultPagination
from .permissions import IsAdmin, IsOwnerOrAdmin, CanDeleteUser
from .models import User
from .tasks import send_temp_password_email
from .enums import UserRole


class RegisterAPIView(APIView):

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")

            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "Logout successful"},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class TokenRefreshAPIView(APIView):

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ["list", "partial_update"]:
            permission_classes = [IsAuthenticated, IsAdmin]
        elif self.action in ["retrieve"]:
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action in ["destroy"]:
            permission_classes = [IsAuthenticated, CanDeleteUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        if request.user.role == UserRole.ADMIN:
            return User.objects.all()
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

    def retrieve(self, request, pk=None):
        if request.user.role == UserRole.ADMIN:
            user = get_object_or_404(User, pk=pk)
        else:
            user = get_object_or_404(User, pk=pk, is_active=True)

        self.check_object_permissions(request, user)

        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)

        is_active = request.data.get("is_active", None)
        if str(is_active).lower() not in ["true"]:
            raise ValidationError({"detail": "To restore a user, set is_active=true."})

        if user.is_active:
            return Response(
                {"detail": "User is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.deleted_at = None
        user.save()

        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)

        self.check_object_permissions(request, user)

        if not user.is_active:
            return Response(
                {"error": "User is already deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.deleted_at = timezone.now()
        user.save()

        Recipe.objects.filter(user=user, is_active=True).update(
            is_active=False,
            deleted_at=timezone.now(),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class SendTempPasswordEmailView(APIView):
    def post(self, request):
        serializer = TempPasswordEmailSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        send_temp_password_email.delay(email)

        return Response(
            {"message": "Temporary password has been sent to the provided email."},
            status=status.HTTP_202_ACCEPTED,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password updated successfully."}, status=status.HTTP_200_OK
        )
