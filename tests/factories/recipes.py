import factory
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory
from recipes.models import Cuisine, Ingredient, Recipe


class CuisineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cuisine

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Faker("word")
    is_active = True


class IngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ingredient

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Faker("word")
    is_active = True


class RecipeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Recipe

    tenant = factory.SubFactory(TenantFactory)
    user = factory.SubFactory(UserFactory)
    cuisine = factory.SubFactory(CuisineFactory)
    name = factory.Faker("word")
    description = factory.Faker("paragraph")
    preparation_steps = factory.Faker("text")
    cooking_time = factory.Faker("random_int", min=10, max=120)
    sharing_status = "PRIVATE"
    is_active = True
