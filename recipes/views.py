from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Cuisine, Ingredient, Recipe, RecipeIngredient
from .permissions import IsAdmin, IsOwnerOrAdmin, CanViewRecipe
from .serializers import (
    CuisineSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeListSerializer,
)
from common.pagination import DefaultPagination
from users.enums import UserRole


class CuisineViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        if request.user.role == UserRole.ADMIN:
            return Cuisine.objects.all()
        return Cuisine.objects.filter(is_active=True)

    def list(self, request):
        cuisines = self.get_queryset(request)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(cuisines, request)

        serializer = CuisineSerializer(
            paginated_qs, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        cuisines = self.get_queryset(request)
        cuisine = get_object_or_404(cuisines, pk=pk)
        serializer = CuisineSerializer(cuisine, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name")

        old = Cuisine.objects.filter(name=name, is_active=False).first()

        if old:
            old.is_active = True
            old.deleted_at = None
            old.save()
            serializer = CuisineSerializer(old, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = CuisineSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        cuisine = get_object_or_404(Cuisine, pk=pk, is_active=True)
        serializer = CuisineSerializer(
            cuisine, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        cuisine = get_object_or_404(Cuisine, pk=pk, is_active=True)

        is_used = Recipe.objects.filter(cuisine=cuisine, is_active=True).exists()

        if is_used:
            return Response(
                {
                    "error": "Cannot delete cuisine because it is used in one or more active recipes."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cuisine.is_active = False
        cuisine.deleted_at = timezone.now()
        cuisine.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ViewSet):
    lookup_field = "pk"
    lookup_value_converter = "uuid"

    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        if request.user.role == UserRole.ADMIN:
            return Ingredient.objects.all()
        return Ingredient.objects.filter(is_active=True)

    def list(self, request):
        ingredients = self.get_queryset(request)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(ingredients, request)

        serializer = IngredientSerializer(
            paginated_qs, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        ingredients = self.get_queryset(request)
        ingredient = get_object_or_404(ingredients, pk=pk)
        serializer = IngredientSerializer(ingredient, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name")

        old = Ingredient.objects.filter(name=name, is_active=False).first()

        if old:
            old.is_active = True
            old.deleted_at = None
            old.save()
            serializer = IngredientSerializer(old, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = IngredientSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, is_active=True)
        serializer = IngredientSerializer(
            ingredient, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, is_active=True)

        is_used = RecipeIngredient.objects.filter(
            ingredient=ingredient, recipe__is_active=True
        ).exists()

        if is_used:
            return Response(
                {
                    "error": "Cannot delete ingredient because it is used in one or more active recipes."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ingredient.is_active = False
        ingredient.deleted_at = timezone.now()
        ingredient.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ViewSet):

    def get_permissions(self):
        if self.action in ["partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        elif self.action == "retrieve":
            permission_classes = [IsAuthenticated, CanViewRecipe]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        user = request.user

        if user.role == UserRole.ADMIN:
            return Recipe.objects.all()
        else:
            return Recipe.objects.filter(
                Q(user=user) | Q(sharing_status="PUBLIC"),
                is_active=True,
            )

    def list(self, request):
        recipes = (
            self.get_queryset(request)
            .select_related("user", "cuisine")
            .prefetch_related("ingredients")
        )

        cuisine_ids_param = request.query_params.get("cuisine_id")
        if cuisine_ids_param:
            cuisine_ids = [
                cuisine_id.strip()
                for cuisine_id in cuisine_ids_param.split(",")
                if cuisine_id.strip()
            ]

            recipes = recipes.filter(cuisine__id__in=cuisine_ids)

        sharing_status = request.query_params.get("sharing_status")
        if sharing_status:
            recipes = recipes.filter(sharing_status=sharing_status)

        ingredient_ids_param = request.query_params.get("ingredient_id")
        if ingredient_ids_param:
            ingredient_ids = [
                ingredient_id.strip()
                for ingredient_id in ingredient_ids_param.split(",")
                if ingredient_id.strip()
            ]

            recipes = recipes.filter(
                recipe_ingredients__ingredient__id__in=ingredient_ids
            ).distinct()

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(recipes, request)

        serializer = RecipeListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        qs = (
            self.get_queryset(request)
            .select_related("user", "cuisine")
            .prefetch_related("recipe_ingredients__ingredient")
        )

        recipe = get_object_or_404(qs, pk=pk)

        self.check_object_permissions(request, recipe)
        serializer = RecipeSerializer(recipe, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = RecipeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk, is_active=True)
        self.check_object_permissions(request, recipe)

        serializer = RecipeSerializer(
            recipe, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk, is_active=True)
        self.check_object_permissions(request, recipe)

        recipe.is_active = False
        recipe.deleted_at = timezone.now()
        recipe.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
