from rest_framework import serializers
from .models import User
from django.db import models
from django.contrib.auth.password_validation import validate_password


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
