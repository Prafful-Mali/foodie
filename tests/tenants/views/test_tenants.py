import pytest
from unittest.mock import patch
from django.urls import reverse
from faker import Faker
from tests.factories.tenants import TenantFactory
from tenants.models import Tenant

fake = Faker()

@pytest.mark.django_db
class TestTenantCRUDIntegration:
    # --- CREATE ---
    def test_create_tenant_as_superadmin(self, superadmin_client):
        payload = {"name": fake.pystr(min_chars=10, max_chars=20), "is_premium": True}
        response = superadmin_client.post(reverse("tenant-list"), data=payload)
        
        assert response.status_code == 201, response.data
        assert response.data["name"] == payload["name"]
        assert Tenant.objects.filter(name=payload["name"]).exists()

    def test_create_tenant_as_admin(self, admin_client):
        payload = {"name": fake.company()}
        response = admin_client.post(reverse("tenant-list"), data=payload)
        assert response.status_code == 403

    def test_create_recreate_inactive_tenant(self, superadmin_client):
        # Setup an inactive tenant
        name = fake.pystr(min_chars=10, max_chars=20)
        TenantFactory(name=name, is_active=False)
        
        payload = {"name": name, "is_premium": True}
        response = superadmin_client.post(reverse("tenant-list"), data=payload)
        
        assert response.status_code == 201
        assert response.data["is_active"] is True
        assert response.data["is_premium"] is True

    # --- LIST ---
    def test_list_tenants_as_superadmin(self, superadmin_client):
        TenantFactory.create_batch(3)
        response = superadmin_client.get(reverse("tenant-list"))
        
        assert response.status_code == 200, response.data
        # At least 4 (3 new + 1 from superadmin_client setup)
        assert len(response.data["results"]) >= 3

    def test_list_tenants_filters(self, superadmin_client):
        TenantFactory(is_active=True, is_premium=True)
        TenantFactory(is_active=False, is_premium=False)
        
        response = superadmin_client.get(reverse("tenant-list") + "?is_active=false&is_premium=false")
        assert response.status_code == 200
        for item in response.data["results"]:
            assert item["is_active"] is False
            assert item["is_premium"] is False

    # --- RETRIEVE ---
    def test_retrieve_tenant(self, superadmin_client):
        tenant = TenantFactory()
        response = superadmin_client.get(
            reverse("tenant-detail", kwargs={"pk": tenant.pk})
        )
        assert response.status_code == 200, response.data
        assert response.data["id"] == str(tenant.pk)
        assert response.data["name"] == tenant.name

    def test_retrieve_tenant_as_normal_admin(self, admin_client):
        tenant = TenantFactory()
        response = admin_client.get(
            reverse("tenant-detail", kwargs={"pk": tenant.pk})
        )
        assert response.status_code == 403

    # --- PARTIAL UPDATE (PATCH) ---
    def test_partial_update_tenant(self, superadmin_client):
        tenant = TenantFactory()
        new_name = fake.pystr(min_chars=10, max_chars=20)
        response = superadmin_client.patch(
            reverse("tenant-detail", kwargs={"pk": tenant.pk}),
            data={"name": new_name},
            format="json"
        )
        assert response.status_code == 200, response.data
        tenant.refresh_from_db()
        assert tenant.name == new_name

    @patch("tenants.views.restore_tenant_related_data")
    def test_restore_tenant_triggers_celery(self, mock_task, superadmin_client):
        from django.utils import timezone
        
        tenant = TenantFactory(is_active=False)
        deleted_timestamp = timezone.now()
        tenant.deleted_at = deleted_timestamp
        tenant.save()
        
        response = superadmin_client.patch(
            reverse("tenant-detail", kwargs={"pk": tenant.pk}),
            data={"is_active": True},
            format="json"
        )
        
        assert response.status_code == 200
        tenant.refresh_from_db()
        assert tenant.is_active is True
        
        # Verify celery task was dispatched
        mock_task.delay.assert_called_once_with(str(tenant.id), deleted_timestamp.isoformat())

    # --- DESTROY (DELETE) ---
    @patch("tenants.views.soft_delete_tenant_related_data")
    def test_delete_tenant(self, mock_task, superadmin_client):
        tenant = TenantFactory()
        response = superadmin_client.delete(
            reverse("tenant-detail", kwargs={"pk": tenant.pk})
        )
        assert response.status_code == 204
        
        tenant.refresh_from_db()
        assert not tenant.is_active
        assert tenant.deleted_at is not None
        
        mock_task.delay.assert_called_once_with(str(tenant.id), tenant.deleted_at.isoformat())
