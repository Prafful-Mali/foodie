import pytest
from django.db import IntegrityError
from tests.factories.recipes import (
    CuisineFactory,
    IngredientFactory,
    RecipeFactory,
    RecipeIngredientFactory,
    RecipePictureFactory,
)
from tests.factories.tenants import TenantFactory


@pytest.mark.django_db
class TestCuisineModel:
    def test_cuisine_creation(self):
        cuisine = CuisineFactory(name="Italian")
        assert cuisine.name == "Italian"
        assert str(cuisine) == "Italian"

    def test_unique_cuisine_per_tenant(self):
        tenant = TenantFactory()
        CuisineFactory(tenant=tenant, name="Italian")
        with pytest.raises(IntegrityError):
            CuisineFactory(tenant=tenant, name="Italian")


@pytest.mark.django_db
class TestIngredientModel:
    def test_ingredient_creation(self):
        ingredient = IngredientFactory(name="Tomato")
        assert ingredient.name == "Tomato"
        assert str(ingredient) == "Tomato"

    def test_unique_ingredient_per_tenant(self):
        tenant = TenantFactory()
        IngredientFactory(tenant=tenant, name="Tomato")
        with pytest.raises(IntegrityError):
            IngredientFactory(tenant=tenant, name="Tomato")


@pytest.mark.django_db
class TestRecipeModel:
    def test_recipe_creation(self):
        recipe = RecipeFactory(name="Pizza")
        assert recipe.name == "Pizza"
        assert str(recipe) == "Pizza"
        assert recipe.sharing_status == "PRIVATE"

    def test_unique_recipe_name_per_tenant(self):
        tenant = TenantFactory()
        RecipeFactory(tenant=tenant, name="Pizza")
        with pytest.raises(IntegrityError):
            RecipeFactory(tenant=tenant, name="Pizza")


@pytest.mark.django_db
class TestRecipeIngredientModel:
    def test_recipe_ingredient_creation(self):
        recipe_ingredient = RecipeIngredientFactory()
        assert (
            str(recipe_ingredient)
            == f"{recipe_ingredient.recipe.name} - {recipe_ingredient.ingredient.name}"
        )


@pytest.mark.django_db
class TestRecipePictureModel:
    def test_recipe_picture_creation(self):
        picture = RecipePictureFactory(order=1)
        assert str(picture) == f"{picture.recipe.name} - Picture 1"
