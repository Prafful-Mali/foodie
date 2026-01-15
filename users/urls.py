from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    TokenRefreshAPIView,
    ChangePasswordView,
    UserViewSet,
    VerifyOTPAPIView,
    ResendOTPAPIView,
    ForgotPasswordAPIView,
    ResetPasswordPage,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefreshAPIView.as_view(), name="token_refresh"),
    path(
        "users/change-password/", ChangePasswordView.as_view(), name="password_change"
    ),
    path("auth/verify-otp/", VerifyOTPAPIView.as_view(), name="verify_otp"),
    path("auth/resend-otp/", ResendOTPAPIView.as_view(), name="resend_otp"),
    path("forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot_password"),
    path(
        "reset-password/<str:token>/",
        ResetPasswordPage.as_view(),
        name="reset_password",
    ),
    path("", include(router.urls)),
]
