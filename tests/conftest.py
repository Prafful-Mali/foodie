import pytest
from rest_framework.test import APIClient
from tests.factories.users import UserFactory
from tests.factories.tenants import TenantFactory

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def tenant():
    return TenantFactory()

@pytest.fixture
def user(tenant):
    return UserFactory(tenant=tenant)

@pytest.fixture
def get_auth_headers():
    def _get_headers(user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
    return _get_headers

@pytest.fixture
def authenticated_client(api_client, user, get_auth_headers):
    api_client.credentials(**get_auth_headers(user))
    return api_client

@pytest.fixture
def admin_user(tenant):
    from common.enums import UserRole
    return UserFactory(tenant=tenant, role=UserRole.ADMIN)

@pytest.fixture
def admin_client(api_client, admin_user, get_auth_headers):
    api_client.credentials(**get_auth_headers(admin_user))
    return api_client

@pytest.fixture
def superadmin_user(tenant):
    from common.enums import UserRole
    return UserFactory(tenant=tenant, role=UserRole.SUPERADMIN, is_superadmin=True)

@pytest.fixture
def superadmin_client(api_client, superadmin_user, get_auth_headers):
    api_client.credentials(**get_auth_headers(superadmin_user))
    return api_client
