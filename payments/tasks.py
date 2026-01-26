import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import Payment, Subscription, WebhookEvent
from common.enums import SubscriptionStatus, PaymentStatus

logger = logging.getLogger(__name__)


@shared_task
def process_webhook_event(webhook_event_id):
    try:
        with transaction.atomic():
            webhook_event = WebhookEvent.objects.select_for_update().get(
                id=webhook_event_id
            )
            
            if webhook_event.processed:
                logger.info(f"Webhook {webhook_event_id} already processed, skipping")
                return {
                    "status": "skipped",
                    "webhook_event_id": str(webhook_event_id),
                    "message": "Already processed"
                }

            payload = webhook_event.payload
            event_type = webhook_event.event_type
            
            payment_entity = (
                payload.get("payload", {}).get("payment", {}).get("entity", {})
            )
            payment_id = payment_entity.get("id")

            payment = webhook_event.payment
            
            if event_type == "payment.authorized":
                payment.payment_id = payment_id
                payment.status = PaymentStatus.AUTHORIZED
                payment.method = payment_entity.get("method")
                payment.email = payment_entity.get("email")
                payment.contact = payment_entity.get("contact")
                payment.save()
                
                logger.info(f"Payment {payment.order_id} authorized")

            elif event_type == "payment.captured":
                payment.payment_id = payment_id
                payment.status = PaymentStatus.CAPTURED
                payment.captured = True
                payment.method = payment_entity.get("method")
                payment.email = payment_entity.get("email")
                payment.contact = payment_entity.get("contact")
                
                fee = payment_entity.get("fee", 0)
                tax = payment_entity.get("tax", 0)
                payment.fee = fee / 100 if fee else 0
                payment.tax = tax / 100 if tax else 0
                payment.save()

                subscription = payment.subscription
                subscription.status = SubscriptionStatus.PAID
                subscription.activated_at = (
                    subscription.activated_at or timezone.now()
                )
                subscription.save()

                tenant = subscription.tenant
                tenant.is_premium = True
                tenant.save(update_fields=["is_premium"])
                
                logger.info(
                    f"Payment {payment.order_id} captured - "
                    f"PREMIUM GRANTED to tenant {tenant.id}"
                )

            elif event_type == "payment.failed":
                payment.status = PaymentStatus.FAILED
                payment.error_code = payment_entity.get("error_code")
                payment.error_description = payment_entity.get("error_description")
                payment.save()

                subscription = payment.subscription
                subscription.status = SubscriptionStatus.FAILED
                subscription.save()
                
                logger.warning(f"Payment {payment.order_id} failed")

            webhook_event.processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

        logger.info(
            f"Successfully processed webhook {webhook_event_id} of type {event_type}"
        )
        
        return {
            "status": "success",
            "webhook_event_id": str(webhook_event_id),
            "event_type": event_type,
            "message": "Webhook processed successfully"
        }

    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook event {webhook_event_id} not found")
        return {
            "status": "error",
            "webhook_event_id": str(webhook_event_id),
            "message": "Webhook event not found"
        }
    
    except Exception as e:
        logger.error(
            f"Failed to process webhook {webhook_event_id}: {str(e)}", 
            exc_info=True
        )
        
        try:
            with transaction.atomic():
                webhook_event = WebhookEvent.objects.select_for_update().get(
                    id=webhook_event_id
                )
                webhook_event.processing_error = str(e)
                webhook_event.save(update_fields=["processing_error"])
        except Exception as update_error:
            logger.error(
                f"Failed to update webhook error: {str(update_error)}", 
                exc_info=True
            )
        
        return {
            "status": "error",
            "webhook_event_id": str(webhook_event_id),
            "message": str(e)
        }