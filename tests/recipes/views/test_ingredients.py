import pytest
from django.urls import reverse
from faker import Faker
from tests.factories.recipes import IngredientFactory, RecipeFactory
from recipes.models import Ingredient, RecipeIngredient

fake = Faker()


@pytest.mark.django_db
class TestIngredientCRUDIntegration:
    # --- CREATE ---
    def test_create_ingredient_as_admin(self, admin_client, tenant):
        payload = {"name": fake.word()}
        response = admin_client.post(reverse("ingredient-list"), data=payload)
        assert response.status_code == 201
        assert response.data["name"] == payload["name"]
        assert Ingredient.objects.filter(name=payload["name"], tenant=tenant).exists()

    def test_create_ingredient_as_user(self, authenticated_client):
        payload = {"name": fake.word()}
        response = authenticated_client.post(reverse("ingredient-list"), data=payload)
        assert response.status_code == 403

    # --- LIST ---
    def test_list_ingredients(self, authenticated_client, tenant):
        IngredientFactory.create_batch(3, tenant=tenant)
        IngredientFactory.create_batch(2)  # Different tenant
        response = authenticated_client.get(reverse("ingredient-list"))
        assert response.status_code == 200
        # Check against paginated response
        assert len(response.data["results"]) == 3

    # --- RETRIEVE ---
    def test_retrieve_ingredient(self, authenticated_client, tenant):
        ingredient = IngredientFactory(tenant=tenant)
        response = authenticated_client.get(
            reverse("ingredient-detail", kwargs={"pk": ingredient.pk})
        )
        assert response.status_code == 200
        assert response.data["id"] == str(ingredient.pk)
        assert response.data["name"] == ingredient.name

    def test_retrieve_nonexistent_ingredient(self, authenticated_client):
        import uuid

        response = authenticated_client.get(
            reverse("ingredient-detail", kwargs={"pk": uuid.uuid4()})
        )
        assert response.status_code == 404

    # --- PARTIAL UPDATE ---
    def test_partial_update_ingredient_as_admin(self, admin_client, tenant):
        ingredient = IngredientFactory(tenant=tenant)
        new_name = fake.word()
        response = admin_client.patch(
            reverse("ingredient-detail", kwargs={"pk": ingredient.pk}),
            data={"name": new_name},
        )
        assert response.status_code == 200
        ingredient.refresh_from_db()
        assert ingredient.name == new_name

    def test_partial_update_ingredient_as_user(self, authenticated_client, tenant):
        ingredient = IngredientFactory(tenant=tenant)
        response = authenticated_client.patch(
            reverse("ingredient-detail", kwargs={"pk": ingredient.pk}),
            data={"name": fake.word()},
        )
        assert response.status_code == 403

    # --- DESTROY ---
    def test_delete_ingredient_as_admin(self, admin_client, tenant):
        ingredient = IngredientFactory(tenant=tenant)
        response = admin_client.delete(
            reverse("ingredient-detail", kwargs={"pk": ingredient.pk})
        )
        assert response.status_code == 204
        ingredient.refresh_from_db()
        assert not ingredient.is_active

    def test_delete_ingredient_used_in_recipe(self, admin_client, tenant):
        ingredient = IngredientFactory(tenant=tenant)
        recipe = RecipeFactory(tenant=tenant, is_active=True)
        RecipeIngredient.objects.create(
            tenant=tenant, recipe=recipe, ingredient=ingredient, quantity=1, unit="kg"
        )

        response = admin_client.delete(
            reverse("ingredient-detail", kwargs={"pk": ingredient.pk})
        )
        assert response.status_code == 400
        assert "Cannot delete ingredient" in str(response.data)

    def test_delete_ingredient_as_user(self, authenticated_client, tenant):
        ingredient = IngredientFactory(tenant=tenant)
        response = authenticated_client.delete(
            reverse("ingredient-detail", kwargs={"pk": ingredient.pk})
        )
        assert response.status_code == 403
