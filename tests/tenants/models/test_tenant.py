import pytest
from tests.factories.tenants import TenantFactory


@pytest.mark.django_db
class TestTenantModel:
    def test_tenant_creation(self):
        tenant = TenantFactory(name="Foodie Corp")
        assert tenant.name == "Foodie Corp"
        assert tenant.is_active is True
        assert tenant.is_premium is False
        assert str(tenant) == "Foodie Corp"

    def test_tenant_basemodel_fields(self):
        tenant = TenantFactory()
        assert tenant.created_at is not None
        assert tenant.updated_at is not None
        assert tenant.deleted_at is None
