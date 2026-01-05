from django.db import models
from django.utils.crypto import get_random_string
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class RegisterSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(min_length=3, max_length=150)
    first_name = serializers.CharField(min_length=3, max_length=150)
    last_name = serializers.CharField(min_length=3, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_username(self, attr):
        if User.objects.filter(username=attr).exists():
            raise serializers.ValidationError("username already exists.")
        if " " in attr:
            raise serializers.ValidationError("Username cannot contain spaces.")
        return attr

    def validate_first_name(self, attr):
        if not attr.isalpha():
            raise serializers.ValidationError("First name must contain only letters.")
        return attr

    def validate_last_name(self, attr):
        if not attr.isalpha():
            raise serializers.ValidationError("Last name must contain only letters.")
        return attr

    def validate_email(self, attr):
        attr = attr.lower()

        if User.objects.filter(email=attr).exists():
            raise serializers.ValidationError("Email already exists.")

        return attr

    def validate_password(self, attr):
        validate_password(attr)
        return attr

    def validate(self, data):
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email").lower()
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")

        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        token_str = attrs["refresh"]

        try:
            old_refresh = RefreshToken(token_str)

            old_refresh.blacklist()

            user = User.objects.get(id=old_refresh["user_id"])

            new_refresh = RefreshToken.for_user(user)

            return {
                "refresh": str(new_refresh),
                "access": str(new_refresh.access_token),
            }

        except Exception:
            raise serializers.ValidationError(
                {"refresh": "Invalid or expired refresh token."}
            )


class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "is_active",
            "created_at",
        ]


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "created_at",
            "updated_at",
        ]
