import re
from rest_framework import serializers
from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "is_active",
            "is_premium",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Tenant name cannot be empty.")
        return re.sub(r"\s+", " ", value.strip())


class TenantListSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "is_active",
            "is_premium",
            "user_count",
            "created_at",
        ]
        read_only_fields = fields
