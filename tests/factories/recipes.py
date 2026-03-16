import factory
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory
from recipes.models import Cuisine, Ingredient, Recipe, RecipeIngredient, RecipePicture


class CuisineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cuisine

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Cuisine {n}")
    is_active = True


class IngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ingredient

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Ingredient {n}")
    is_active = True


class RecipeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Recipe

    tenant = factory.SubFactory(TenantFactory)
    user = factory.SubFactory(UserFactory)
    cuisine = factory.SubFactory(CuisineFactory, tenant=factory.SelfAttribute("..tenant"))
    name = factory.Sequence(lambda n: f"Recipe {n}")
    description = factory.Faker("paragraph")
    preparation_steps = factory.Faker("text")
    cooking_time = factory.Faker("random_int", min=10, max=120)
    sharing_status = "PRIVATE"
    is_active = True


class RecipeIngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecipeIngredient

    tenant = factory.SubFactory(TenantFactory)
    recipe = factory.SubFactory(RecipeFactory, tenant=factory.SelfAttribute("..tenant"))
    ingredient = factory.SubFactory(IngredientFactory, tenant=factory.SelfAttribute("..tenant"))
    quantity = 1.0
    unit = "cup"


class RecipePictureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecipePicture

    tenant = factory.SubFactory(TenantFactory)
    recipe = factory.SubFactory(RecipeFactory, tenant=factory.SelfAttribute("..tenant"))
    picture = factory.django.ImageField(color="blue")
    order = factory.Sequence(lambda n: n)

