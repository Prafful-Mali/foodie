from rest_framework import serializers
from .models import Cuisine, Ingredient


class CuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
