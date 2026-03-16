import pytest
from django.db import IntegrityError
from tests.factories.users import UserFactory
from tests.factories.tenants import TenantFactory


@pytest.mark.django_db
class TestUserModel:
    def test_user_creation(self):
        user = UserFactory(email="test@example.com", tenant=None)
        assert user.email == "test@example.com"
        assert not user.is_superadmin
        assert str(user) == "test@example.com"

    def test_user_str_with_tenant(self):
        tenant = TenantFactory(name="Test Tenant")
        user = UserFactory(email="tenant@example.com", tenant=tenant)
        assert str(user) == "tenant@example.com (Test Tenant)"

    def test_user_email_uniqueness(self):
        UserFactory(email="unique@example.com")
        with pytest.raises(IntegrityError):
            UserFactory(email="unique@example.com")

    def test_user_role_default(self):
        from common.enums import UserRole

        user = UserFactory()
        assert user.role == UserRole.USER
