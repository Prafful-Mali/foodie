from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    TokenRefreshAPIView,
    SendTempPasswordEmailView,
    ChangePasswordView,
    UserViewSet,
    VerifyOTPAPIView,
    ResendOTPAPIView,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefreshAPIView.as_view(), name="token_refresh"),
    path("password-reset/", SendTempPasswordEmailView.as_view(), name="password_reset"),
    path(
        "users/change-password/", ChangePasswordView.as_view(), name="password_change"
    ),
    path("auth/verify-otp/", VerifyOTPAPIView.as_view(), name="verify_otp"),
    path("auth/resend-otp/", ResendOTPAPIView.as_view(), name="resend_otp"),
    path("", include(router.urls)),
]
