import uuid
from django.db import models
from common.models import BaseModel


from .enums import SubscriptionStatus, PaymentStatus


class Subscription(BaseModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    amount = models.PositiveIntegerField(help_text="Amount in paise")
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
    )
    is_active = models.BooleanField(default=True, db_default=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Subscription({self.tenant_id}, {self.status})"


class Payment(BaseModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    subscription = models.OneToOneField(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    order_id = models.CharField(max_length=100, unique=True)
    payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    amount = models.PositiveIntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=10, default="INR")

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
    )

    method = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)

    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    captured = models.BooleanField(default=False)

    error_code = models.CharField(max_length=100, null=True, blank=True)
    error_description = models.TextField(null=True, blank=True)

    razorpay_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment({self.order_id}, {self.status})"


class WebhookEvent(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="webhook_events",
    )

    event_id = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event_id"],
                name="unique_webhook_event_id",
            )
        ]

    def __str__(self):
        return self.event_type
