import pytest
from unittest.mock import patch
from django.urls import reverse
from faker import Faker
from tests.factories.users import UserFactory
from users.models import User

fake = Faker()

@pytest.mark.django_db
class TestAuthAPIIntegration:
    
    @patch('users.views.auth.send_login_otp_email')
    def test_login_request_otp(self, mock_task, api_client, user):
        payload = {"email": user.email, "password": "testpass123"}
        response = api_client.post(reverse("login"), data=payload)
        
        assert response.status_code == 202
        assert "OTP sent" in response.data["message"]
        mock_task.delay.assert_called_once_with(user.email)

    def test_login_invalid_credentials(self, api_client, user):
        payload = {"email": user.email, "password": "wrongpassword"}
        response = api_client.post(reverse("login"), data=payload)
        assert response.status_code == 400
        
    @patch('users.views.auth.is_otp_rate_limited', return_value=False)
    @patch('users.views.auth.send_login_otp_email')
    def test_login_resend_otp(self, mock_task, mock_rate_limit, api_client, user):
        payload = {"email": user.email, "password": "testpass123"}
        response = api_client.post(reverse("login_resend_otp"), data=payload)
        assert response.status_code == 202
        mock_task.delay.assert_called_once_with(user.email)

    @patch('users.serializers.get_user_otp')
    @patch('users.views.auth.delete_user_otp')
    def test_login_verify_otp(self, mock_delete_otp, mock_get_otp, api_client, user):
        from users.utils import hash_otp
        mock_get_otp.return_value = hash_otp("123456")
        payload = {"email": user.email, "otp": "123456"}
        response = api_client.post(reverse("login_verify_otp"), data=payload)
        
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data
        mock_delete_otp.assert_called_once_with(user.email, prefix="login_otp")

    def test_logout(self, authenticated_client, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        payload = {"refresh": str(refresh)}
        response = authenticated_client.post(reverse("logout"), data=payload)
        assert response.status_code == 200
        
        # Test reuse
        response2 = authenticated_client.post(reverse("logout"), data=payload)
        assert response2.status_code == 401

    def test_change_password(self, authenticated_client, user):
        payload = {
            "current_password": "testpass123",
            "new_password": "NewStrongPass123!",
            "new_password_confirm": "NewStrongPass123!"
        }
        response = authenticated_client.post(reverse("password_change"), data=payload)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("NewStrongPass123!")

    @patch('users.views.auth.send_reset_password_email')
    def test_forgot_password(self, mock_task, api_client, user):
        payload = {"email": user.email}
        response = api_client.post(reverse("forgot_password"), data=payload)
        assert response.status_code == 202
        mock_task.delay.assert_called_once()
        
    @patch('users.views.auth.send_invite_email')
    def test_invite_user_as_admin(self, mock_task, admin_client, tenant):
        payload = {
            "email": fake.email(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "role": "USER"
        }
        response = admin_client.post(reverse("invite_user"), data=payload)
        assert response.status_code == 202
        mock_task.delay.assert_called_once()
        invited_user = User.objects.get(email=payload["email"])
        assert invited_user.tenant == tenant
        assert not invited_user.is_active

    def test_invite_user_as_regular_user(self, authenticated_client):
        payload = {"email": fake.email(), "first_name": "Test", "role": "USER"}
        response = authenticated_client.post(reverse("invite_user"), data=payload)
        assert response.status_code == 403
