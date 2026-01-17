from django.db import models


class UserRole(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    USER = "USER", "User"
