from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from ..models import Cuisine, Recipe
from ..permissions import IsAdmin, HasTenant
from ..serializers import CuisineSerializer
from common.pagination import DefaultPagination
from common.enums import UserRole


class CuisineViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ["create", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, HasTenant, IsAdmin]
        else:
            permission_classes = [IsAuthenticated, HasTenant]

        return [permission() for permission in permission_classes]

    def get_queryset(self, request):
        tenant = request.tenant

        if request.user.role == UserRole.ADMIN:
            return Cuisine.objects.filter(tenant=tenant)
        return Cuisine.objects.filter(tenant=tenant, is_active=True)

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
        tenant = request.tenant
        name = request.data.get("name")

        if name:
            old = Cuisine.objects.filter(
                tenant=tenant, name=name.strip(), is_active=False
            ).first()

            if old:
                old.is_active = True
                old.deleted_at = None
                old.save()
                serializer = CuisineSerializer(old, context={"request": request})
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = CuisineSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=tenant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        tenant = request.tenant
        cuisine = get_object_or_404(Cuisine, pk=pk, tenant=tenant, is_active=True)

        serializer = CuisineSerializer(
            cuisine, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        tenant = request.tenant
        cuisine = get_object_or_404(Cuisine, pk=pk, tenant=tenant, is_active=True)

        is_used = Recipe.objects.filter(
            tenant=tenant, cuisine=cuisine, is_active=True
        ).exists()

        if is_used:
            return Response(
                {
                    "errors": {
                        "detail": "Cannot delete cuisine because it is used in one or more active recipes."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cuisine.is_active = False
        cuisine.deleted_at = timezone.now()
        cuisine.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
