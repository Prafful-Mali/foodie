from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from ..models import Recipe, Ingredient, RecipePicture
from ..permissions import IsOwnerOrAdmin, CanViewRecipe, HasTenant
from ..serializers import (
    RecipeSerializer,
    RecipeListSerializer,
)
from common.pagination import DefaultPagination
from common.enums import UserRole


class RecipeViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ["partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, HasTenant, IsOwnerOrAdmin]
        elif self.action == "retrieve":
            permission_classes = [IsAuthenticated, HasTenant, CanViewRecipe]
        else:
            permission_classes = [IsAuthenticated, HasTenant]

        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        user = request.user
        tenant = request.tenant

        if user.role == UserRole.ADMIN:
            return Recipe.objects.filter(tenant=tenant)
        else:
            return Recipe.objects.filter(
                Q(user=user) | Q(sharing_status="PUBLIC"),
                tenant=tenant,
                is_active=True,
            )

    def list(self, request):
        recipes = (
            self.get_queryset(request)
            .select_related("user", "cuisine")
            .prefetch_related(
                Prefetch(
                    "ingredients",
                    queryset=Ingredient.objects.only("id", "name")
                ),
                Prefetch(
                    "recipe_pictures",
                    queryset=RecipePicture.objects.filter(is_active=True).only("id", "picture", "order")
                )
            )
            .only(
                "id",
                "name",
                "description",
                "cooking_time",
                "sharing_status",
                "created_at",
                "user__id",
                "cuisine__id",
                "cuisine__name",
            )
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
            .prefetch_related(
                "recipe_ingredients__ingredient",
                "recipe_pictures"
            )
        )

        recipe = get_object_or_404(qs, pk=pk)

        self.check_object_permissions(request, recipe)
        serializer = RecipeSerializer(recipe, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = RecipeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        target_user_id = serializer.validated_data.pop("target_user_id", None)

        if target_user_id and request.user.role == UserRole.ADMIN:
            from users.models import User

            target_user = User.objects.get(id=target_user_id)
            serializer.save(user=target_user)
        else:
            serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        tenant = request.tenant
        recipe = get_object_or_404(Recipe, pk=pk, tenant=tenant, is_active=True)
        self.check_object_permissions(request, recipe)

        serializer = RecipeSerializer(
            recipe, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        tenant = request.tenant
        recipe = get_object_or_404(Recipe, pk=pk, tenant=tenant, is_active=True)
        self.check_object_permissions(request, recipe)

        recipe.is_active = False
        recipe.deleted_at = timezone.now()
        recipe.save()

        return Response(status=status.HTTP_204_NO_CONTENT)