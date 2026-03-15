import pytest
from unittest.mock import patch
from django.urls import reverse
from faker import Faker
from tests.factories.users import UserFactory
from common.enums import UserRole
from users.models import User

fake = Faker()


@pytest.mark.django_db
class TestUserCRUDIntegration:
    # --- CREATE (by admin) ---
    @patch("users.views.user.send_setup_password_email")
    def test_create_user_as_admin(self, mock_task, admin_client, tenant):
        payload = {
            "username": fake.user_name(),
            "email": fake.email(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "role": "USER",
        }
        response = admin_client.post(reverse("user-list"), data=payload, format="json")
        assert response.status_code == 201
        assert (
            response.data["message"]
            == "User created successfully. An email has been sent to them to set their password."
        )

        created_user = User.objects.get(email=payload["email"])
        assert created_user.tenant == tenant
        mock_task.delay.assert_called_once()

    def test_create_user_as_regular_user(self, authenticated_client):
        response = authenticated_client.post(
            reverse("user-list"), data={"email": fake.email()}
        )
        assert response.status_code == 403

    # --- LIST ---
    def test_list_users_as_admin(self, admin_client, tenant):
        # Create users in same tenant
        UserFactory.create_batch(3, tenant=tenant)
        # Create a user in different tenant to ensure isolation
        UserFactory.create_batch(2)

        response = admin_client.get(reverse("user-list"))
        assert response.status_code == 200
        # 3 users + the admin_client caller himself = 4
        assert len(response.data["results"]) == 4
        for u in response.data["results"]:
            assert u["tenant_id"] == str(tenant.id)

    def test_list_users_filters(self, admin_client, tenant):
        UserFactory(tenant=tenant, is_active=True)
        UserFactory(tenant=tenant, is_active=False)

        # ?status=deleted
        response = admin_client.get(reverse("user-list") + "?status=deleted")
        assert response.status_code == 200
        for u in response.data["results"]:
            assert not u["is_active"]

        # ?status=active (should return admin + newly created active)
        response2 = admin_client.get(reverse("user-list") + "?status=active")
        for u in response2.data["results"]:
            assert u["is_active"]

    def test_list_users_as_regular_user(self, authenticated_client):
        response = authenticated_client.get(reverse("user-list"))
        assert response.status_code == 403

    # --- RETRIEVE ---
    def test_retrieve_user_as_admin(self, admin_client, tenant):
        other_user = UserFactory(tenant=tenant)
        response = admin_client.get(
            reverse("user-detail", kwargs={"pk": other_user.pk})
        )
        assert response.status_code == 200
        assert response.data["email"] == other_user.email

    def test_retrieve_self(self, authenticated_client, user):
        response = authenticated_client.get(
            reverse("user-detail", kwargs={"pk": user.pk})
        )
        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_retrieve_other_user_as_regular(self, authenticated_client, tenant):
        other_user = UserFactory(tenant=tenant)
        response = authenticated_client.get(
            reverse("user-detail", kwargs={"pk": other_user.pk})
        )
        assert response.status_code == 403

    # --- UPDATE (PATCH) ---
    def test_partial_update_self(self, authenticated_client, user):
        new_name = fake.first_name()
        response = authenticated_client.patch(
            reverse("user-detail", kwargs={"pk": user.pk}),
            data={"first_name": new_name},
            format="json",
        )
        assert response.status_code == 403

    def test_partial_update_other_as_admin(self, admin_client, tenant):
        other_user = UserFactory(tenant=tenant)
        new_name = fake.last_name()
        response = admin_client.patch(
            reverse("user-detail", kwargs={"pk": other_user.pk}),
            data={"last_name": new_name},
            format="json",
        )
        assert response.status_code == 200
        other_user.refresh_from_db()
        assert other_user.last_name == new_name

    @patch("users.views.user.restore_user_resources")
    def test_restore_deleted_user(self, mock_task, admin_client, tenant):
        from django.utils import timezone

        deleted_user = UserFactory(tenant=tenant, is_active=False)
        deleted_user.deleted_at = timezone.now()
        deleted_user.save()

        response = admin_client.patch(
            reverse("user-detail", kwargs={"pk": deleted_user.pk}),
            data={"is_active": True},
            format="json",
        )
        assert response.status_code == 200
        deleted_user.refresh_from_db()
        assert deleted_user.is_active
        mock_task.delay.assert_called_once()

    # --- DELETE ---
    @patch("users.views.user.deactivate_user_resources")
    def test_delete_user_as_admin(self, mock_task, admin_client, tenant):
        user_to_delete = UserFactory(tenant=tenant)
        response = admin_client.delete(
            reverse("user-detail", kwargs={"pk": user_to_delete.pk})
        )
        assert response.status_code == 204
        user_to_delete.refresh_from_db()
        assert not user_to_delete.is_active
        assert user_to_delete.deleted_by is not None
        mock_task.delay.assert_called_once()

    def test_delete_other_user_as_regular(self, authenticated_client, tenant):
        other_user = UserFactory(tenant=tenant)
        response = authenticated_client.delete(
            reverse("user-detail", kwargs={"pk": other_user.pk})
        )
        assert response.status_code == 403

    def test_delete_self_as_regular(self, authenticated_client, user):
        response = authenticated_client.delete(
            reverse("user-detail", kwargs={"pk": user.pk})
        )
        assert response.status_code == 204
        user.refresh_from_db()
        assert not user.is_active
