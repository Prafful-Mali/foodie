from django.db import models


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"


class PaymentStatus(models.TextChoices):
    CREATED = "created", "Created"
    CAPTURED = "captured", "Captured"
    FAILED = "failed", "Failed"
