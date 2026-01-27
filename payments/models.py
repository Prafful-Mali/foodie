import uuid
from django.db import models
from django.conf import settings
from common.models import BaseModel
from common.enums import SubscriptionStatus, PaymentStatus


class Subscription(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_subscriptions",
    )
    amount = models.PositiveIntegerField(help_text="Amount in paise")
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
    )
    is_active = models.BooleanField(default=True, db_default=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription({self.tenant.name}, {self.status})"


class Payment(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    order_id = models.CharField(max_length=100, unique=True, db_index=True)
    payment_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True, db_index=True
    )

    amount = models.PositiveIntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True,
    )
    method = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    captured = models.BooleanField(default=False, db_default=False)

    error_code = models.CharField(max_length=100, null=True, blank=True)
    error_description = models.TextField(null=True, blank=True)

    verified_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment({self.order_id}, {self.status})"


class WebhookEvent(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique event ID from Razorpay",
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
    )

    payload = models.JSONField(help_text="Complete webhook payload")

    processed = models.BooleanField(default=False, db_default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(null=True, blank=True)

    order_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    payment_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"
