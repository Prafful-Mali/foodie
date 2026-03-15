import pytest
from django.urls import reverse
from faker import Faker
from tests.factories.recipes import CuisineFactory, IngredientFactory, RecipeFactory
from recipes.models import Recipe, RecipeIngredient

fake = Faker()

@pytest.mark.django_db
class TestRecipeCRUDIntegration:
    # --- CREATE ---
    def test_create_recipe(self, authenticated_client, tenant, user):
        cuisine = CuisineFactory(tenant=tenant)
        ingredient = IngredientFactory(tenant=tenant)

        payload = {
            "name": fake.pystr(min_chars=10, max_chars=20),
            "description": fake.paragraph(),
            "preparation_steps": fake.text(),
            "cooking_time": fake.random_int(min=10, max=120),
            "sharing_status": "PRIVATE",
            "cuisine_id": str(cuisine.id),
            "recipe_ingredients": [
                {
                    "ingredient_id": str(ingredient.id),
                    "quantity": "2.50",
                    "unit": "cups"
                }
            ]
        }
        
        response = authenticated_client.post(
            reverse("recipe-list"),
            data=payload,
            format="json"
        )
        assert response.status_code == 201, response.data
        assert response.data["name"] == payload["name"]
        assert Recipe.objects.filter(name=payload["name"], tenant=tenant).exists()
        recipe = Recipe.objects.get(name=payload["name"], tenant=tenant)
        assert recipe.user == user
        assert RecipeIngredient.objects.filter(recipe=recipe, ingredient=ingredient).exists()

    # --- LIST ---
    def test_list_recipes(self, authenticated_client, tenant, user):
        RecipeFactory.create_batch(3, tenant=tenant, user=user)
        RecipeFactory.create_batch(2, tenant=tenant)  # Different user
        response = authenticated_client.get(reverse("recipe-list"))
        assert response.status_code == 200, response.data
        # By default list only shows user's own recipes or PUBLIC
        # Thus the 3 created by user should be present
        assert len(response.data["results"]) == 3

    def test_list_recipes_public(self, authenticated_client, tenant, user):
        RecipeFactory(tenant=tenant, user=user, sharing_status="PRIVATE")
        RecipeFactory(tenant=tenant, sharing_status="PUBLIC")  # other user's public recipe
        response = authenticated_client.get(reverse("recipe-list"))
        assert response.status_code == 200, response.data
        assert len(response.data["results"]) == 2

    # --- RETRIEVE ---
    def test_retrieve_recipe(self, authenticated_client, tenant, user):
        recipe = RecipeFactory(tenant=tenant, user=user)
        response = authenticated_client.get(
            reverse("recipe-detail", kwargs={"pk": recipe.pk})
        )
        assert response.status_code == 200, response.data
        assert response.data["id"] == str(recipe.pk)
        assert response.data["name"] == recipe.name

    def test_retrieve_nonexistent_recipe(self, authenticated_client):
        import uuid
        response = authenticated_client.get(
            reverse("recipe-detail", kwargs={"pk": uuid.uuid4()})
        )
        assert response.status_code == 404

    # --- PARTIAL UPDATE (PATCH) ---
    def test_partial_update_recipe(self, authenticated_client, tenant, user):
        recipe = RecipeFactory(tenant=tenant, user=user)
        new_name = fake.pystr(min_chars=10, max_chars=20)
        response = authenticated_client.patch(
            reverse("recipe-detail", kwargs={"pk": recipe.pk}),
            data={"name": new_name},
            format="json"
        )
        assert response.status_code == 200, response.data
        recipe.refresh_from_db()
        assert recipe.name == new_name

    def test_partial_update_other_user_recipe(self, authenticated_client, tenant):
        # another user's recipe
        recipe = RecipeFactory(tenant=tenant, sharing_status="PUBLIC")
        response = authenticated_client.patch(
            reverse("recipe-detail", kwargs={"pk": recipe.pk}),
            data={"name": fake.sentence(nb_words=3)[:100]},
            format="json"
        )
        # Should be forbidden to edit another user's recipe
        assert response.status_code == 403

    # --- DESTROY (DELETE) ---
    def test_delete_recipe(self, authenticated_client, tenant, user):
        recipe = RecipeFactory(tenant=tenant, user=user)
        response = authenticated_client.delete(
            reverse("recipe-detail", kwargs={"pk": recipe.pk})
        )
        assert response.status_code == 204
        recipe.refresh_from_db()
        assert not recipe.is_active

    def test_delete_other_user_recipe(self, authenticated_client, tenant):
        recipe = RecipeFactory(tenant=tenant)
        response = authenticated_client.delete(
            reverse("recipe-detail", kwargs={"pk": recipe.pk})
        )
        assert response.status_code == 403
