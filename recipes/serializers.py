import re
from users.models import User
from rest_framework import serializers
from .models import Cuisine, Ingredient, Recipe, RecipeIngredient, RecipePicture
from common.enums import UserRole


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
                self.fields["is_active"] = serializers.BooleanField(read_only=True)
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)

    def validate_name(self, value):
        request = self.context.get("request")
        if not request or not request.tenant:
            raise serializers.ValidationError("User must belong to a tenant.")

        value = re.sub(r"\s+", " ", value.strip())

        if not all(x.isalpha() or x.isspace() for x in value):
            raise serializers.ValidationError(
                "Cuisine name must contain only alphabets and spaces."
            )

        tenant = request.tenant
        queryset = Cuisine.objects.filter(tenant=tenant, name=value, is_active=True)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A cuisine with this name already exists in your organization."
            )

        return value


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
                self.fields["is_active"] = serializers.BooleanField(read_only=True)
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)

    def validate_name(self, value):
        request = self.context.get("request")
        if not request or not request.tenant:
            raise serializers.ValidationError("User must belong to a tenant.")

        value = re.sub(r"\s+", " ", value.strip())

        if not all(x.isalpha() or x.isspace() for x in value):
            raise serializers.ValidationError(
                "Ingredient name must contain only alphabets and spaces."
            )

        tenant = request.tenant
        queryset = Ingredient.objects.filter(tenant=tenant, name=value, is_active=True)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "An ingredient with this name already exists in your organization."
            )

        return value


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.UUIDField(write_only=True)
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ["id", "ingredient_id", "ingredient", "quantity", "unit"]
        read_only_fields = ["id"]

    def validate_ingredient_id(self, value):
        request = self.context.get("request")
        if not request or not request.tenant:
            raise serializers.ValidationError("User must belong to a tenant.")

        tenant = request.tenant

        if not Ingredient.objects.filter(
            id=value, tenant=tenant, is_active=True
        ).exists():
            raise serializers.ValidationError(
                "Ingredient does not exist or is inactive in your organization."
            )
        return value


class RecipePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipePicture
        fields = ["id", "picture", "order"]
        read_only_fields = ["id"]


class RecipeSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    target_user_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )
    cuisine_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    cuisine = CuisineSerializer(read_only=True)
    recipe_ingredients = RecipeIngredientSerializer(many=True, required=False)
    recipe_pictures = RecipePictureSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "user_id",
            "target_user_id",
            "cuisine_id",
            "cuisine",
            "name",
            "description",
            "preparation_steps",
            "cooking_time",
            "sharing_status",
            "recipe_ingredients",
            "recipe_pictures",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request:
            if request.user.role == UserRole.ADMIN:
                self.fields["is_active"] = serializers.BooleanField(read_only=True)
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)

    def validate_target_user_id(self, value):
        if value is None:
            return value

        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")

        if request.user.role != UserRole.ADMIN:
            raise serializers.ValidationError(
                "Only admins can create recipes for other users."
            )

        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("User does not exist or is inactive.")

        return value

    def validate_cuisine_id(self, value):
        if value is None:
            return value

        request = self.context.get("request")
        if not request or not request.tenant:
            raise serializers.ValidationError("User must belong to a tenant.")

        tenant = request.tenant

        if not Cuisine.objects.filter(id=value, tenant=tenant, is_active=True).exists():
            raise serializers.ValidationError(
                "Cuisine does not exist or is inactive in your organization."
            )

        return value

    def validate_name(self, value):
        request = self.context.get("request")
        if not request or not request.tenant:
            raise serializers.ValidationError("User must belong to a tenant.")

        value = re.sub(r"\s+", " ", value.strip())

        if not all(x.isalpha() or x.isspace() for x in value):
            raise serializers.ValidationError(
                "Recipe name must contain only alphabets and spaces."
            )

        tenant = request.tenant
        queryset = Recipe.objects.filter(tenant=tenant, name=value, is_active=True)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A recipe with this name already exists in your organization."
            )

        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.tenant:
            raise serializers.ValidationError("User must belong to a tenant.")

        if not request.tenant.is_premium:
            from common.constants import RECIPE_CAP

            current_count = Recipe.objects.filter(
                tenant=request.tenant, is_active=True
            ).count()

            if current_count >= RECIPE_CAP:
                raise serializers.ValidationError(
                    f"You have reached the maximum limit of {RECIPE_CAP} recipes. Please upgrade to premium to add more."
                )

        return attrs

    def create(self, validated_data):
        recipe_ingredients_data = validated_data.pop("recipe_ingredients", [])
        cuisine_id = validated_data.pop("cuisine_id", None)

        request = self.context.get("request")
        tenant = request.tenant

        if cuisine_id:
            validated_data["cuisine"] = Cuisine.objects.get(
                id=cuisine_id, tenant=tenant
            )

        validated_data["tenant"] = tenant
        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in recipe_ingredients_data:
            ingredient_id = ingredient_data.pop("ingredient_id")
            ingredient = Ingredient.objects.get(id=ingredient_id, tenant=tenant)
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, tenant=tenant, **ingredient_data
            )

        files = request.FILES.getlist("recipe_pictures")
        for idx, file in enumerate(files):
            RecipePicture.objects.create(
                recipe=recipe,
                tenant=tenant,
                picture=file,
                order=idx,
            )
        return recipe

    def update(self, instance, validated_data):
        recipe_ingredients_data = validated_data.pop("recipe_ingredients", None)
        cuisine_id = validated_data.pop("cuisine_id", None)

        request = self.context.get("request")
        tenant = request.tenant

        if "cuisine_id" in self.initial_data:
            if cuisine_id:
                instance.cuisine = Cuisine.objects.get(id=cuisine_id, tenant=tenant)
            else:
                instance.cuisine = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if recipe_ingredients_data is not None:
            instance.recipe_ingredients.all().delete()

            for ingredient_data in recipe_ingredients_data:
                ingredient_id = ingredient_data.pop("ingredient_id")
                ingredient = Ingredient.objects.get(id=ingredient_id, tenant=tenant)
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    tenant=tenant,
                    **ingredient_data,
                )

        return instance


class MiniIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class MiniCuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class RecipeListSerializer(serializers.ModelSerializer):
    cuisine = MiniCuisineSerializer(read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    ingredients = MiniIngredientSerializer(many=True, read_only=True)
    recipe_pictures = RecipePictureSerializer(many=True, read_only=True)

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
            "recipe_pictures", 
            "created_at",
        ]
        read_only_fields = fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request:
            if request.user.role == UserRole.ADMIN:
                self.fields["is_active"] = serializers.BooleanField(read_only=True)
                self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)