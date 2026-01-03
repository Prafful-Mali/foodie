from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Cuisine, Ingredient
from .permissions import IsAdmin
from .serializers import CuisineSerializer, IngredientSerializer
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
