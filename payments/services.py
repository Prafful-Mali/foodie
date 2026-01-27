import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
import razorpay

from .models import Subscription, Payment, WebhookEvent
from common.enums import SubscriptionStatus, PaymentStatus
from common.constants import LIFETIME_AMOUNT_PAISE

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    @transaction.atomic
    def create_subscription(self, tenant, user) -> Tuple[Subscription, Payment, Dict]:
        existing = Subscription.objects.filter(
            tenant=tenant, status=SubscriptionStatus.PAID, is_active=True
        ).first()

        if existing:
            raise ValidationError("An active subscription already exists")

        amount = LIFETIME_AMOUNT_PAISE

        subscription = Subscription.objects.create(
            tenant=tenant,
            created_by=user,
            amount=amount,
            status=SubscriptionStatus.PENDING,
        )

        try:
            order = self.client.order.create(
                {
                    "amount": amount,
                    "currency": "INR",
                    "payment_capture": 1,
                }
            )
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}")
            raise ValidationError(f"Failed to create payment order: {str(e)}")

        payment = Payment.objects.create(
            tenant=tenant,
            subscription=subscription,
            user=user,
            order_id=order["id"],
            amount=amount,
            status=PaymentStatus.CREATED,
        )

        logger.info(f"Created subscription {subscription.id} for tenant {tenant.id}")
        return subscription, payment, order

    @transaction.atomic
    def verify_payment_signature(
        self, payment: Payment, payment_id: str, signature: str
    ) -> bool:
        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": payment.order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                }
            )
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return False

        if payment.status == PaymentStatus.CREATED:
            payment.payment_id = payment_id
            payment.status = PaymentStatus.VERIFIED
            payment.verified_at = timezone.now()
            payment.save(
                update_fields=["payment_id", "status", "verified_at", "updated_at"]
            )
            logger.info(f"Payment {payment.order_id} signature verified")

        return True

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        try:
            self.client.utility.verify_webhook_signature(
                body=body, signature=signature, secret=settings.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False

    @transaction.atomic
    def store_webhook(
        self, event_id: str, event_type: str, payload: Dict
    ) -> Tuple[WebhookEvent, bool]:
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        webhook, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": payload,
                "order_id": order_id,
                "payment_id": payment_id,
                "processed": False,
            },
        )

        return webhook, created

    @transaction.atomic
    def process_webhook(self, webhook_event: WebhookEvent) -> Dict:
        webhook_event = WebhookEvent.objects.select_for_update().get(
            id=webhook_event.id
        )

        if webhook_event.processed:
            logger.info(f"Webhook {webhook_event.event_id} already processed")
            return {"status": "already_processed"}

        payload = webhook_event.payload
        event_type = webhook_event.event_type

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")

        if not order_id:
            error = "No order_id in webhook"
            webhook_event.processing_error = error
            webhook_event.save()
            return {"status": "error", "message": error}

        payment = (
            Payment.objects.filter(order_id=order_id)
            .select_related("subscription", "tenant")
            .first()
        )
        if not payment:
            error = f"Payment not found for order_id {order_id}"
            webhook_event.processing_error = error
            webhook_event.save()
            return {"status": "error", "message": error}

        try:
            if event_type == "payment.authorized":
                self.handle_authorized(payment, payment_entity)

            elif event_type == "payment.captured":
                self.handle_captured(payment, payment_entity)

            elif event_type == "payment.failed":
                self.handle_failed(payment, payment_entity)

            webhook_event.processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            logger.info(f"Webhook {webhook_event.event_id} processed successfully")
            return {"status": "success"}

        except Exception as e:
            error = str(e)
            webhook_event.processing_error = error
            webhook_event.save()
            logger.error(f"Webhook processing failed: {error}", exc_info=True)
            return {"status": "error", "message": error}

    @transaction.atomic
    def handle_authorized(self, payment: Payment, payment_entity: Dict):
        payment.payment_id = payment_entity.get("id")
        payment.status = PaymentStatus.AUTHORIZED
        payment.method = payment_entity.get("method")
        payment.email = payment_entity.get("email")
        payment.contact = payment_entity.get("contact")
        payment.save()
        logger.info(f"Payment {payment.order_id} authorized")

    @transaction.atomic
    def handle_captured(self, payment: Payment, payment_entity: Dict):
        payment.payment_id = payment_entity.get("id")
        payment.status = PaymentStatus.CAPTURED
        payment.captured = True
        payment.captured_at = timezone.now()
        payment.method = payment_entity.get("method")
        payment.email = payment_entity.get("email")
        payment.contact = payment_entity.get("contact")

        fee = payment_entity.get("fee", 0)
        tax = payment_entity.get("tax", 0)
        payment.fee = fee or 0
        payment.tax = tax or 0
        payment.save()

        subscription = payment.subscription
        subscription.status = SubscriptionStatus.PAID
        subscription.activated_at = subscription.activated_at or timezone.now()
        subscription.save()

        tenant = subscription.tenant
        if not tenant.is_premium:
            tenant.is_premium = True
            tenant.save(update_fields=["is_premium"])

        logger.info(
            f"Payment {payment.order_id} captured - PREMIUM GRANTED to tenant {tenant.id}"
        )

    @transaction.atomic
    def handle_failed(self, payment: Payment, payment_entity: Dict):
        payment.status = PaymentStatus.FAILED
        payment.error_code = payment_entity.get("error_code")
        payment.error_description = payment_entity.get("error_description")
        payment.save()

        subscription = payment.subscription
        subscription.status = SubscriptionStatus.FAILED
        subscription.save()

        logger.warning(f"Payment {payment.order_id} failed")
