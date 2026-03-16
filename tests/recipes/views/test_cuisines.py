import pytest
from django.urls import reverse
from faker import Faker
from tests.factories.recipes import CuisineFactory, RecipeFactory
from recipes.models import Cuisine

fake = Faker()


@pytest.mark.django_db
class TestCuisineCRUDIntegration:
    # --- CREATE ---
    def test_create_cuisine_as_admin(self, admin_client, tenant):
        payload = {"name": fake.word()}
        response = admin_client.post(reverse("cuisine-list"), data=payload)
        assert response.status_code == 201
        assert response.data["name"] == payload["name"]
        assert Cuisine.objects.filter(name=payload["name"], tenant=tenant).exists()

    def test_create_cuisine_as_user(self, authenticated_client):
        payload = {"name": fake.word()}
        response = authenticated_client.post(reverse("cuisine-list"), data=payload)
        assert response.status_code == 403

    # --- LIST ---
    def test_list_cuisines(self, authenticated_client, tenant):
        CuisineFactory.create_batch(3, tenant=tenant)
        CuisineFactory.create_batch(2)  # Different tenant
        response = authenticated_client.get(reverse("cuisine-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) == 3

    # --- RETRIEVE ---
    def test_retrieve_cuisine(self, authenticated_client, tenant):
        cuisine = CuisineFactory(tenant=tenant)
        response = authenticated_client.get(
            reverse("cuisine-detail", kwargs={"pk": cuisine.pk})
        )
        assert response.status_code == 200
        assert response.data["id"] == str(cuisine.pk)
        assert response.data["name"] == cuisine.name

    def test_retrieve_nonexistent_cuisine(self, authenticated_client):
        import uuid

        response = authenticated_client.get(
            reverse("cuisine-detail", kwargs={"pk": uuid.uuid4()})
        )
        assert response.status_code == 404

    # --- PARTIAL UPDATE ---
    def test_partial_update_cuisine_as_admin(self, admin_client, tenant):
        cuisine = CuisineFactory(tenant=tenant)
        new_name = fake.word()
        response = admin_client.patch(
            reverse("cuisine-detail", kwargs={"pk": cuisine.pk}),
            data={"name": new_name},
        )
        assert response.status_code == 200
        cuisine.refresh_from_db()
        assert cuisine.name == new_name

    def test_partial_update_cuisine_as_user(self, authenticated_client, tenant):
        cuisine = CuisineFactory(tenant=tenant)
        response = authenticated_client.patch(
            reverse("cuisine-detail", kwargs={"pk": cuisine.pk}),
            data={"name": fake.word()},
        )
        assert response.status_code == 403

    # --- DESTROY ---
    def test_delete_cuisine_as_admin(self, admin_client, tenant):
        cuisine = CuisineFactory(tenant=tenant)
        response = admin_client.delete(
            reverse("cuisine-detail", kwargs={"pk": cuisine.pk})
        )
        assert response.status_code == 204
        cuisine.refresh_from_db()
        assert not cuisine.is_active

    def test_delete_cuisine_used_in_recipe(self, admin_client, tenant):
        cuisine = CuisineFactory(tenant=tenant)
        RecipeFactory(tenant=tenant, cuisine=cuisine, is_active=True)
        response = admin_client.delete(
            reverse("cuisine-detail", kwargs={"pk": cuisine.pk})
        )
        assert response.status_code == 400
        assert "Cannot delete cuisine" in str(response.data)

    def test_delete_cuisine_as_user(self, authenticated_client, tenant):
        cuisine = CuisineFactory(tenant=tenant)
        response = authenticated_client.delete(
            reverse("cuisine-detail", kwargs={"pk": cuisine.pk})
        )
        assert response.status_code == 403
