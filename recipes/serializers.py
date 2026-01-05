from rest_framework import serializers
from .models import Cuisine, Ingredient, Recipe, RecipeIngredient
from users.enums import UserRole


class CuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request:
            if request.user.role == UserRole.ADMIN:
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request:
            if request.user.role == UserRole.ADMIN:
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.UUIDField(write_only=True)
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ["id", "ingredient_id", "ingredient", "quantity", "unit"]
        read_only_fields = ["id"]

    def validate_ingredient_id(self, value):
        if not Ingredient.objects.filter(id=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Ingredient does not exist.")
        return value


class RecipeSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    cuisine_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    cuisine = CuisineSerializer(read_only=True)
    recipe_ingredients = RecipeIngredientSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "user_id",
            "cuisine_id",
            "cuisine",
            "name",
            "description",
            "preparation_steps",
            "cooking_time",
            "sharing_status",
            "recipe_ingredients",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request:
            if request.user.role == UserRole.ADMIN:
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)

    def validate_cuisine_id(self, value):
        if value is None:
            return value

        if not Cuisine.objects.filter(id=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Cuisine does not exist.")

        return value

    def create(self, validated_data):
        recipe_ingredients_data = validated_data.pop("recipe_ingredients", [])
        cuisine_id = validated_data.pop("cuisine_id", None)

        if cuisine_id:
            validated_data["cuisine"] = Cuisine.objects.get(id=cuisine_id)

        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in recipe_ingredients_data:
            ingredient_id = ingredient_data.pop("ingredient_id")
            ingredient = Ingredient.objects.get(id=ingredient_id)
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, **ingredient_data
            )

        return recipe

    def update(self, instance, validated_data):
        recipe_ingredients_data = validated_data.pop("recipe_ingredients", None)
        cuisine_id = validated_data.pop("cuisine_id", None)

        if "cuisine_id" in self.initial_data:
            if cuisine_id:
                instance.cuisine = Cuisine.objects.get(id=cuisine_id)
            else:
                instance.cuisine = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if recipe_ingredients_data is not None:
            instance.recipe_ingredients.all().delete()

            for ingredient_data in recipe_ingredients_data:
                ingredient_id = ingredient_data.pop("ingredient_id")
                ingredient = Ingredient.objects.get(id=ingredient_id)
                RecipeIngredient.objects.create(
                    recipe=instance, ingredient=ingredient, **ingredient_data
                )

        return instance


class MiniIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class RecipeListSerializer(serializers.ModelSerializer):
    cuisine = CuisineSerializer(read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    ingredients = MiniIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "user_id",
            "cuisine",
            "name",
            "description",
            "ingredients",
            "cooking_time",
            "sharing_status",
            "created_at",
        ]
        read_only_fields = fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request:
            if request.user.role == UserRole.ADMIN:
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)
