from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from ..models import Ingredient, RecipeIngredient
from ..permissions import IsAdmin, HasTenant
from ..serializers import IngredientSerializer
from common.pagination import DefaultPagination
from common.enums import UserRole
from common.constants import INGREDIENT_CACHE_TIMEOUT


class IngredientViewSet(viewsets.ViewSet):
    lookup_field = "pk"
    lookup_value_converter = "uuid"

    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, HasTenant, IsAdmin]
        else:
            permission_classes = [IsAuthenticated, HasTenant]

        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        tenant = request.tenant

        if request.user.role == UserRole.ADMIN:
            return Ingredient.objects.filter(tenant=tenant)
        return Ingredient.objects.filter(tenant=tenant, is_active=True)

    def list(self, request):
        user = request.user
        tenant = request.tenant
        query_params = request.query_params.urlencode()

        cache_key = f"ingredients_list_{tenant.id}_{user.id}_{query_params}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        ingredients = self.get_queryset(request)

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(ingredients, request)

        serializer = IngredientSerializer(
            paginated_qs, many=True, context={"request": request}
        )
        response = paginator.get_paginated_response(serializer.data)

        cache.set(cache_key, response.data, timeout=INGREDIENT_CACHE_TIMEOUT)

        return response

    def retrieve(self, request, pk=None):
        ingredients = self.get_queryset(request)
        ingredient = get_object_or_404(ingredients, pk=pk)
        serializer = IngredientSerializer(ingredient, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        tenant = request.tenant
        name = request.data.get("name")

        if name:
            old = Ingredient.objects.filter(
                tenant=tenant, name=name.strip(), is_active=False
            ).first()

            if old:
                old.is_active = True
                old.deleted_at = None
                old.save()
                self._clear_ingredient_cache(tenant.id)
                serializer = IngredientSerializer(old, context={"request": request})
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = IngredientSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=tenant)
        self._clear_ingredient_cache(tenant.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        tenant = request.tenant
        ingredient = get_object_or_404(Ingredient, pk=pk, tenant=tenant, is_active=True)

        serializer = IngredientSerializer(
            ingredient, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self._clear_ingredient_cache(tenant.id)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        tenant = request.tenant
        ingredient = get_object_or_404(Ingredient, pk=pk, tenant=tenant, is_active=True)

        is_used = RecipeIngredient.objects.filter(
            tenant=tenant, ingredient=ingredient, recipe__is_active=True
        ).exists()

        if is_used:
            return Response(
                {
                    "errors": {
                        "detail": "Cannot delete ingredient because it is used in one or more active recipes."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ingredient.is_active = False
        ingredient.deleted_at = timezone.now()
        ingredient.save()

        self._clear_ingredient_cache(tenant.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _clear_ingredient_cache(self, tenant_id):
        try:
            cache.delete_pattern(f"ingredients_list_{tenant_id}_*")
        except AttributeError:
            pass
