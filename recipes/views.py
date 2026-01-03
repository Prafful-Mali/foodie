from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Cuisine
from .permissions import IsAdmin
from .serializers import CuisineSerializer
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
