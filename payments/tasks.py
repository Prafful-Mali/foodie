import logging
from celery import shared_task

from .models import WebhookEvent
from .services import PaymentService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_webhook_task(self, webhook_id: str):
    try:
        webhook = WebhookEvent.objects.get(id=webhook_id)
        service = PaymentService()
        result = service.process_webhook(webhook)
        logger.info(f"Webhook {webhook_id} processed: {result['status']}")
        return result

    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook {webhook_id} not found")
        return {"status": "error", "message": "Webhook not found"}

    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for webhook {webhook_id}")
            return {"status": "error", "message": str(e)}
