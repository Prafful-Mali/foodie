import uuid
from django.db import models
from django.conf import settings
from common.models import BaseModel
from .enums import SharingStatus


class Cuisine(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="cuisines",
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="unique_cuisine_per_tenant",
            )
        ]

    def __str__(self):
        return self.name


class Ingredient(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="unique_ingredient_per_tenant",
            )
        ]

    def __str__(self):
        return self.name


class Recipe(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    cuisine = models.ForeignKey(
        Cuisine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipes",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preparation_steps = models.TextField()
    cooking_time = models.PositiveIntegerField()
    sharing_status = models.CharField(
        max_length=20,
        choices=SharingStatus.choices,
        default=SharingStatus.PRIVATE,
    )
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", related_name="recipes"
    )
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="unique_recipe_name_per_tenant",
            )
        ]

    def __str__(self):
        return self.name


class RecipeIngredient(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "recipe", "ingredient"],
                name="unique_ingredient_per_recipe_per_tenant",
            )
        ]

    def __str__(self):
        return f"{self.recipe.name} - {self.ingredient.name}"
