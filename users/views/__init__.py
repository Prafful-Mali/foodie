from .auth import (
    RegisterAPIView,
    VerifyOTPAPIView,
    ResendOTPAPIView,
    LoginAPIView,
    LoginVerifyOTPAPIView,
    LoginResendOTPAPIView,
    LogoutAPIView,
    TokenRefreshAPIView,
    ChangePasswordView,
    ForgotPasswordAPIView,
    ResetPasswordPage,
    SetupPasswordPage,
)
from .user import UserViewSet
