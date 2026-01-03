from django.urls import path
from .views import RegisterAPIView, LoginAPIView, LogoutAPIView, TokenRefreshAPIView

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefreshAPIView.as_view(), name="token_refresh"),
]
