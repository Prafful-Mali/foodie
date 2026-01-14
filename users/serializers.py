from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .enums import UserRole


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
        user = User.objects.filter(username=attr).first()

        if not user:
            return attr

        # Allow self-deleted user to restore
        if not user.is_active and user.deleted_by_id == user.id:
            return attr

        raise serializers.ValidationError("Username already exists.")

    def validate_first_name(self, attr):
        if not attr.isalpha():
            raise serializers.ValidationError("First name must contain only letters.")
        return attr

    def validate_last_name(self, attr):
        if not attr.isalpha():
            raise serializers.ValidationError("Last name must contain only letters.")
        return attr

    def validate_email(self, value):
        value = value.lower()
        user = User.objects.filter(email=value).first()

        if not user:
            return value

        if user.is_active:
            raise serializers.ValidationError("Email already exists.")

        if user.deleted_by and user.deleted_by_id != user.id:
            raise serializers.ValidationError(
                "This account was deactivated by an administrator."
            )

        if user.deleted_by_id == user.id:
            return value

        raise serializers.ValidationError("Email already exists.")

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
        email = validated_data.get("email").lower()

        user = User.objects.filter(email=email).first()

        if user and not user.is_active and user.deleted_by_id == user.id:
            user.username = validated_data["username"]
            user.first_name = validated_data["first_name"]
            user.last_name = validated_data["last_name"]
            user.set_password(password)

            user.is_active = True
            user.deleted_at = None
            user.deleted_by = None

            user.save(
                update_fields=[
                    "username",
                    "first_name",
                    "last_name",
                    "password",
                    "is_active",
                    "deleted_at",
                    "deleted_by",
                ]
            )
            return user

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

    def validate_email(self, attr):
        attr = attr.lower()
        try:
            user = User.objects.get(email=attr)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account does not exist"})

        if user.is_email_verified:
            raise serializers.ValidationError({"detail": "Email already verified"})

        return attr


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, attr):
        attr.lower()
        try:
            user = User.objects.get(email=attr)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account does not exist"})

        if user.is_email_verified:
            raise serializers.ValidationError({"detail": "Email already verified"})

        return attr


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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.role == UserRole.ADMIN:
            self.fields["is_active"] = serializers.BooleanField()
            self.fields["deleted_at"] = serializers.DateTimeField(read_only=True)


class TempPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower()

        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email.")

        if not user.is_active:
            raise serializers.ValidationError(
                "Account with this email is disabled. Please contact admin."
            )

        return value


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
