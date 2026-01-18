from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Tenant
from .permissions import IsSuperAdmin
from .serializers import TenantSerializer, TenantListSerializer
from common.pagination import DefaultPagination


class TenantViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return Tenant.objects.all()

    def list(self, request):
        tenants = self.get_queryset().annotate(
            user_count=Count("users", filter=Q(users__is_active=True))
        )

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "true":
                tenants = tenants.filter(is_active=True)
            elif is_active.lower() == "false":
                tenants = tenants.filter(is_active=False)

        is_premium = request.query_params.get("is_premium")
        if is_premium is not None:
            if is_premium.lower() == "true":
                tenants = tenants.filter(is_premium=True)
            elif is_premium.lower() == "false":
                tenants = tenants.filter(is_premium=False)

        tenants = tenants.order_by("-created_at")

        paginator = DefaultPagination()
        paginated_qs = paginator.paginate_queryset(tenants, request)

        serializer = TenantListSerializer(paginated_qs, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        tenant = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = TenantSerializer(tenant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name")

        if name:
            old_tenant = Tenant.objects.filter(
                name=name.strip(), is_active=False
            ).first()

            if old_tenant:
                old_tenant.is_active = True
                old_tenant.deleted_at = None

                if "is_premium" in request.data:
                    old_tenant.is_premium = request.data["is_premium"]

                old_tenant.save()
                serializer = TenantSerializer(old_tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = TenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        tenant = get_object_or_404(Tenant, pk=pk, is_active=True)

        serializer = TenantSerializer(tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        tenant = get_object_or_404(Tenant, pk=pk, is_active=True)

        active_users_count = tenant.users.filter(is_active=True).count()

        if active_users_count > 0:
            return Response(
                {
                    "error": f"Cannot delete tenant because it has {active_users_count} active user(s). Please remove or delete users first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant.is_active = False
        tenant.deleted_at = timezone.now()
        tenant.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
