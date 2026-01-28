import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from common.enums import UserRole
from tenants.models import Tenant
from .utils import (
    hash_otp,
    delete_reset_token,
    get_user_otp,
)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email").lower()
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        if not user.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Account is disabled. Please contact admin."}
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {"detail": "Please verify your account before login"}
            )

        attrs["email"] = email
        return attrs


class LoginVerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        email = attrs["email"].lower()
        otp = attrs["otp"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account is disabled"})

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {"detail": "Please verify your account before login"}
            )

        cached_otp = get_user_otp(email, prefix="login_otp")

        if not cached_otp:
            raise serializers.ValidationError(
                {"detail": "OTP expired. Please request a new one."}
            )

        if cached_otp != hash_otp(otp):
            raise serializers.ValidationError({"detail": "Invalid OTP"})

        attrs["email"] = email
        attrs["user"] = user
        return attrs


class LoginResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"].lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid email"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account is disabled"})

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {"detail": "Please verify your account first"}
            )

        if get_user_otp(email, prefix="login_otp"):
            raise serializers.ValidationError(
                {
                    "detail": "An OTP was already sent. Please check your email before requesting again."
                }
            )

        attrs["email"] = email
        return attrs


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


class UserSerializer(serializers.ModelSerializer):
    tenant_id = serializers.UUIDField(
        source="tenant.id", read_only=True, allow_null=True
    )
    tenant_name = serializers.CharField(
        source="tenant.name", read_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_email_verified",
            "first_name",
            "last_name",
            "role",
            "tenant_id",
            "tenant_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "role",
            "tenant_id",
            "tenant_name",
            "created_at",
            "updated_at",
        ]

    def validate_first_name(self, value):
        if value and not value.isalpha():
            raise serializers.ValidationError("First name must contain only letters.")
        return value

    def validate_last_name(self, value):
        if value and not value.isalpha():
            raise serializers.ValidationError("Last name must contain only letters.")
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and (
            request.user.role == UserRole.ADMIN or request.user.is_superadmin
        ):
            self.fields["is_active"] = serializers.BooleanField()
            self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.instance
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError("New passwords do not match.")

        validate_password(data["new_password"], self.instance)

        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data["new_password"])
        instance.save()
        return instance


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        qs = User.objects.filter(email=value, is_active=True)

        if not qs.exists():
            raise serializers.ValidationError(
                "No active account exists with this email address."
            )

        return value


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8)
    confirm_new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return attrs


class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150)
    first_name = serializers.CharField(min_length=3, max_length=150)
    last_name = serializers.CharField(min_length=3, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    confirm_password = serializers.CharField(
        write_only=True, min_length=8, required=False
    )
    tenant_id = serializers.UUIDField(required=False, allow_null=True)
    is_email_verified = serializers.BooleanField(read_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value, is_active=True).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_first_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("First name must contain only letters.")
        return value

    def validate_last_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("Last name must contain only letters.")
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        request = self.context.get("request")

        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        tenant_id = attrs.get("tenant_id")

        if request.user.is_superadmin:
            if not tenant_id:
                raise serializers.ValidationError(
                    {
                        "tenant_id": "Tenant ID is required for super admin to create users."
                    }
                )

            if not Tenant.objects.filter(id=tenant_id, is_active=True).exists():
                raise serializers.ValidationError(
                    {"tenant_id": "Invalid or inactive tenant."}
                )

        elif request.user.role == UserRole.ADMIN:
            if tenant_id:
                raise serializers.ValidationError(
                    {"tenant_id": "Normal admins cannot specify tenant_id."}
                )

            if not request.user.tenant:
                raise serializers.ValidationError(
                    {"detail": "Admin must belong to a tenant to create users."}
                )

        else:
            raise serializers.ValidationError(
                {"detail": "Only admins can create users."}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        password = validated_data.pop("password", None)
        request = self.context.get("request")

        if request.user.is_superadmin:
            tenant_id = validated_data.pop("tenant_id")
            tenant = Tenant.objects.get(id=tenant_id)
            user = User(
                **validated_data,
                role=UserRole.ADMIN,
                tenant=tenant,
                is_email_verified=False,
            )
        else:
            validated_data.pop("tenant_id", None)
            user = User(
                **validated_data,
                role=UserRole.USER,
                tenant=request.user.tenant,
                is_email_verified=False,
            )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save()
        return user


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower()
        user = User.objects.filter(email=value).first()

        if user and user.is_active:
            raise serializers.ValidationError("Email already exists.")

        if user and user.deleted_by and user.deleted_by_id != user.id:
            raise serializers.ValidationError(
                "This account was deactivated by an administrator."
            )

        return value

    def create(self, validated_data):
        request = self.context["request"]

        if not request.user.tenant:
            raise serializers.ValidationError(
                {"detail": "Admin must belong to a tenant to invite users."}
            )

        email = validated_data["email"]

        user = User.objects.create(
            email=email,
            tenant=request.user.tenant,
            role=UserRole.USER,
            is_active=False,
            is_email_verified=False,
        )
        user.set_unusable_password()
        user.save()

        return user


class AcceptInviteSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150)
    first_name = serializers.CharField(min_length=3, max_length=150)
    last_name = serializers.CharField(min_length=3, max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        user = User.objects.filter(username=value).first()

        if not user:
            return value

        if not user.is_active and user.deleted_by_id == user.id:
            return value

        raise serializers.ValidationError("Username already exists.")

    def validate_first_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("First name must contain only letters.")
        return value

    def validate_last_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("Last name must contain only letters.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return data

    def create(self, validated_data):
        user_id = self.context["user_id"]
        token = self.context["token"]
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "User not found"})

        user.username = validated_data["username"]
        user.first_name = validated_data["first_name"]
        user.last_name = validated_data["last_name"]
        user.set_password(validated_data["password"])
        user.is_active = True
        user.is_email_verified = True
        user.deleted_at = None
        user.deleted_by = None

        user.save(
            update_fields=[
                "username",
                "first_name",
                "last_name",
                "password",
                "is_active",
                "is_email_verified",
                "deleted_at",
                "deleted_by",
            ]
        )
        delete_reset_token(token)
        return user
