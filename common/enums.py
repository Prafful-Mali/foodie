from django.db import models


class UserRole(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    USER = "USER", "User"


class SharingStatus(models.TextChoices):
    PUBLIC = "PUBLIC", "Public"
    PRIVATE = "PRIVATE", "Private"


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"


class PaymentStatus(models.TextChoices):
    CREATED = "created", "Created"
    AUTHORIZED = "authorized", "Authorized"
    VERIFIED = "verified", "Verified"
    CAPTURED = "captured", "Captured"
    FAILED = "failed", "Failed"
