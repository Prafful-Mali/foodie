import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from common.models import BaseModel
from .enums import UserRole


class User(AbstractUser, BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    is_superadmin = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False, db_default=False)

    deleted_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_users",
    )

    def __str__(self):
        if self.tenant:
            return f"{self.email} ({self.tenant.name})"
        return self.email
