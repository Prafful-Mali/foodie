from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
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
    ChangePasswordSerializer,
    UserSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    LoginVerifyOTPSerializer,
    LoginResendOTPSerializer,
)
from common.pagination import DefaultPagination
from .permissions import IsAdmin, IsOwnerOrAdmin, CanDeleteUser
from .models import User
from .tasks import (
    send_verification_email,
    hard_delete_user,
    send_reset_password_email,
    send_login_otp_email,
)
from .enums import UserRole
from .utils import get_user_id_from_token, delete_reset_token


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        key = f"email:{user.email}"

        if not cache.add(key, True, timeout=300):
            return Response(
                {"error": "Please wait before requesting OTP again"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        send_verification_email.delay(user.email)

        return Response(
            {"message": "Registration successful. OTP sent to email."},
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPAPIView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user_otp = serializer.validated_data["otp"]

        saved_otp = cache.get(f"otp:{email}")
        if not saved_otp:
            return Response(
                {"error": "OTP expired or invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if str(saved_otp) != str(user_otp):
            return Response(
                {"error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

            cache.delete(f"otp:{email}")

            return Response(
                {
                    "message": "Email verified successfully",
                },
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class ResendOTPAPIView(APIView):
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)

            if user.is_email_verified:
                return Response(
                    {"error": "Email already verified"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            key = f"email:{user.email}"
            if not cache.add(key, True, timeout=300):
                return Response(
                    {"error": "Please wait 5 minutes before requesting again"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            send_verification_email.delay(email)

            return Response(
                {"message": "OTP resent successfully"},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class LoginAPIView(APIView):

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        send_login_otp_email.delay(email)

        return Response(
            {
                "message": "OTP sent to your email. Please verify to complete login.",
                "email": email,
            },
            status=status.HTTP_200_OK,
        )


class LoginVerifyOTPAPIView(APIView):
    def post(self, request):
        serializer = LoginVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = serializer.validated_data["user"]

        cache.delete(f"login_otp:{email}")

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


class LoginResendOTPAPIView(APIView):
    def post(self, request):
        serializer = LoginResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        send_login_otp_email.delay(email)

        return Response(
            {"message": "OTP resent successfully"},
            status=status.HTTP_200_OK,
        )


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

        hard_delete_user.apply_async(
            args=[str(user.id)],
            eta=eta,
        )

        Recipe.objects.filter(user=user, is_active=True).update(
            is_active=False,
            deleted_at=now,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password updated successfully."}, status=status.HTTP_200_OK
        )


class ForgotPasswordAPIView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        base_url = request.build_absolute_uri("/")[:-1]

        send_reset_password_email.delay(email, base_url)

        return Response(
            {"message": "If the email exists, a reset link was sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordPage(APIView):

    def get(self, request, token):
        user_id = get_user_id_from_token(token)
        if not user_id:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return render(request, "reset_password.html", {"token": token})

    def post(self, request, token):
        user_id = get_user_id_from_token(token)
        if not user_id:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(id=user_id)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        delete_reset_token(token)

        return Response(
            {"success": True},
            status=status.HTTP_200_OK,
        )
