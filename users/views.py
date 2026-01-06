from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from recipes.models import Recipe
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    AdminUserSerializer,
    AdminUserListSerializer,
    TempPasswordEmailSerializer,
    ChangePasswordSerializer,
)
from .permissions import IsAdmin
from .models import User
from .pagination import DefaultPagination
from .tasks import send_temp_password_email


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data

        return Response(
            {
                "access": tokens.get("access"),
                "refresh": tokens.get("refresh"),
            },
            status=status.HTTP_200_OK,
        )


class AdminUserViewSet(viewsets.ViewSet):
    permission_classes = [IsAdmin]

    def list(self, request):
        status_param = request.query_params.get("status")

        users = User.objects.all()

        if status_param == "active":
            users = users.filter(is_active=True)

        elif status_param == "deleted":
            users = users.filter(is_active=False)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(users, request)

        serializer = AdminUserListSerializer(paginated_qs, many=True)

        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        serializer = AdminUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)

        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response(
                {"error": "Admins cannot delete their own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active:
            return Response(
                {"error": "User is already deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.deleted_at = timezone.now()
        user.save()

        recipes_qs = Recipe.objects.filter(user=user, is_active=True)

        recipes_qs.update(
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
