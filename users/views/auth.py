from django.shortcuts import get_object_or_404, render
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers import (
    RegisterSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    ChangePasswordSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    LoginVerifyOTPSerializer,
    LoginResendOTPSerializer,
)
from ..models import User
from ..tasks import (
    send_verification_email,
    send_reset_password_email,
    send_login_otp_email,
)
from ..utils import get_user_id_from_token, delete_reset_token, hash_otp


class RegisterAPIView(APIView):
    def post(self, request, tenant_id=None):
        data = request.data.copy()
        data["tenant_id"] = tenant_id

        serializer = RegisterSerializer(data=data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        key = f"email:{user.email}"

        if not cache.add(key, True, timeout=300):
            return Response(
                {"errors": {"detail": "Please wait before requesting OTP again"}},
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
                {"errors": {"detail": "OTP expired or invalid"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if str(saved_otp) != hash_otp(str(user_otp)):
            return Response(
                {"errors": {"detail": "Invalid OTP"}},
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
                {"errors": {"detail": "User not found"}},
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
                    {"errors": {"detail": "Email already verified"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            key = f"email:{user.email}"
            if not cache.add(key, True, timeout=300):
                return Response(
                    {"errors": {"detail": "Please wait 5 minutes before requesting again"}},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            send_verification_email.delay(email)

            return Response(
                {"message": "OTP resent successfully"},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"errors": {"detail": "User not found"}},
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
                    {"errors": {"detail": "Refresh token is required"}},
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
                {"errors": {"detail": "Invalid or expired token"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class TokenRefreshAPIView(APIView):

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


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
                {"errors": {"detail": "Invalid or expired token"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return render(request, "reset_password.html", {"token": token})

    def post(self, request, token):
        user_id = get_user_id_from_token(token)
        if not user_id:
            return Response(
                {"errors": {"detail": "Invalid or expired token"}},
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


class SetupPasswordPage(APIView):

    def get(self, request, token):
        user_id = get_user_id_from_token(token)
        if not user_id:
            return Response(
                {"errors": {"detail": "Invalid or expired token"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return render(request, "setup_password.html", {"token": token})

    def post(self, request, token):
        user_id = get_user_id_from_token(token)
        if not user_id:
            return Response(
                {"errors": {"detail": "Invalid or expired token"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(id=user_id)
        user.set_password(serializer.validated_data["new_password"])
        user.is_email_verified = True
        user.save(update_fields=["password", "is_email_verified"])

        delete_reset_token(token)

        return Response(
            {"success": True},
            status=status.HTTP_200_OK,
        )
