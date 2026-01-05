from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Cuisine, Ingredient, Recipe
from .permissions import IsAdmin, IsOwnerOrAdmin
from .serializers import (
    CuisineSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeListSerializer,
)
from .pagination import DefaultPagination


class CuisineViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def list(self, request):
        cuisines = Cuisine.objects.filter(deleted_at__isnull=True)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(cuisines, request)

        serializer = CuisineSerializer(paginated_qs, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        cuisine = get_object_or_404(Cuisine, pk=pk, deleted_at__isnull=True)
        serializer = CuisineSerializer(cuisine)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name")

        old = Cuisine.objects.filter(name=name, deleted_at__isnull=False).first()

        if old:
            old.deleted_at = None
            old.save()
            serializer = CuisineSerializer(old)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = CuisineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        cuisine = get_object_or_404(Cuisine, pk=pk, deleted_at__isnull=True)
        serializer = CuisineSerializer(cuisine, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        cuisine = get_object_or_404(Cuisine, pk=pk, deleted_at__isnull=True)
        cuisine.deleted_at = timezone.now()
        cuisine.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ViewSet):

    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def list(self, request):
        ingredients = Ingredient.objects.filter(deleted_at__isnull=True)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(ingredients, request)

        serializer = IngredientSerializer(paginated_qs, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, deleted_at__isnull=True)
        serializer = IngredientSerializer(ingredient)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name")

        old = Ingredient.objects.filter(name=name, deleted_at__isnull=False).first()

        if old:
            old.deleted_at = None
            old.save()
            serializer = IngredientSerializer(old)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = IngredientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, deleted_at__isnull=True)
        serializer = IngredientSerializer(ingredient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, deleted_at__isnull=True)
        ingredient.deleted_at = timezone.now()
        ingredient.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ViewSet):

    def get_permissions(self):

        if self.action in ["partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def list(self, request):
        user = request.user

        recipes = (
            Recipe.objects.filter(
                Q(user=user) | Q(sharing_status="PUBLIC"),
                deleted_at__isnull=True,
            )
            .select_related("user", "cuisine")
            .prefetch_related("recipe_ingredients__ingredient")
        )

        cuisine_name = request.query_params.get("cuisine_name")
        if cuisine_name:
            recipes = recipes.filter(cuisine__name__icontains=cuisine_name)

        sharing_status = request.query_params.get("sharing_status")
        if sharing_status:
            recipes = recipes.filter(sharing_status=sharing_status)

        ingredient_name_param = request.query_params.get("ingredient_name")
        if ingredient_name_param:
            names = [
                name.strip()
                for name in ingredient_name_param.split(",")
                if name.strip()
            ]

            for name in names:
                recipes = recipes.filter(
                    recipe_ingredients__ingredient__name__icontains=name
                )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(recipes, request)

        serializer = RecipeListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        recipe = get_object_or_404(
            Recipe.objects.select_related("user", "cuisine").prefetch_related(
                "recipe_ingredients__ingredient"
            ),
            pk=pk,
            deleted_at__isnull=True,
        )

        user = request.user

        if recipe.user != user and recipe.sharing_status != "PUBLIC":
            return Response(
                {"message": "You do not have permission to view this recipe."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = RecipeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk, deleted_at__isnull=True)
        self.check_object_permissions(request, recipe)

        serializer = RecipeSerializer(recipe, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk, deleted_at__isnull=True)
        self.check_object_permissions(request, recipe)

        recipe.deleted_at = timezone.now()
        recipe.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
