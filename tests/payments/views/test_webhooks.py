import pytest
import json
from unittest.mock import patch, MagicMock
from django.urls import reverse
from tests.factories.payments import PaymentFactory, SubscriptionFactory, WebhookEventFactory
from common.enums import PaymentStatus, SubscriptionStatus
from payments.models import Payment, Subscription, WebhookEvent

@pytest.mark.django_db
class TestWebhookIntegration:

    @patch('razorpay.Client')
    @patch('payments.views.process_webhook_task')
    def test_webhook_receive_success(self, mock_task, mock_razorpay, api_client):
        # Mocking razorpay signature validation
        mock_client = MagicMock()
        mock_razorpay.return_value = mock_client
        mock_client.utility.verify_webhook_signature.return_value = True

        payload = {
            "id": "evt_test123",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test456",
                        "order_id": "order_test789"
                    }
                }
            }
        }

        # Need to send bare json payload and custom headers as Razorpay does
        response = api_client.post(
            reverse("razorpay-webhook"), 
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="valid_signature"
        )
        
        assert response.status_code == 202
        assert response.data["status"] == "queued"
        
        webhook = WebhookEvent.objects.get(event_id="evt_test123")
        mock_task.delay.assert_called_once_with(str(webhook.id))

    @patch('razorpay.Client')
    def test_webhook_invalid_signature(self, mock_razorpay, api_client):
        import razorpay
        mock_client = MagicMock()
        mock_razorpay.return_value = mock_client
        mock_client.utility.verify_webhook_signature.side_effect = razorpay.errors.SignatureVerificationError("Invalid sig")

        payload = {"event": "payment.captured"}

        response = api_client.post(
            reverse("razorpay-webhook"), 
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="invalid_signature"
        )
        assert response.status_code == 400

    def test_webhook_missing_signature(self, api_client):
        payload = {"event": "payment.captured"}
        response = api_client.post(
            reverse("razorpay-webhook"), 
            data=json.dumps(payload),
            content_type="application/json"
        )
        # Misses HTTP_X_RAZORPAY_SIGNATURE header
        assert response.status_code == 400


@pytest.mark.django_db
class TestWebhookProcessingService:

    def test_process_webhook_authorized(self):
        from payments.services import PaymentService
        subscription = SubscriptionFactory(status=SubscriptionStatus.PENDING)
        payment = PaymentFactory(subscription=subscription, order_id="order_auth", status=PaymentStatus.CREATED)
        
        payload = {
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_auth1",
                        "order_id": "order_auth",
                        "method": "card",
                        "email": "test@example.com",
                        "contact": "9999999999"
                    }
                }
            }
        }
        
        webhook = WebhookEventFactory(event_id="evt_auth1", event_type="payment.authorized", payload=payload)
        
        service = PaymentService()
        result = service.process_webhook(webhook)
        
        assert result["status"] == "success"
        
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.AUTHORIZED
        assert payment.method == "card"
        assert payment.email == "test@example.com"
        
        webhook.refresh_from_db()
        assert webhook.processed

    def test_process_webhook_captured(self):
        from payments.services import PaymentService
        subscription = SubscriptionFactory(status=SubscriptionStatus.PENDING, tenant__is_premium=False)
        payment = PaymentFactory(subscription=subscription, order_id="order_captured", status=PaymentStatus.AUTHORIZED)
        tenant = subscription.tenant
        
        payload = {
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_cap1",
                        "order_id": "order_captured",
                        "method": "upi",
                        "fee": 100,
                        "tax": 18
                    }
                }
            }
        }
        
        webhook = WebhookEventFactory(event_id="evt_cap1", event_type="payment.captured", payload=payload)
        
        service = PaymentService()
        service.process_webhook(webhook)
        
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CAPTURED
        assert payment.captured is True
        assert payment.fee == 100
        
        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.PAID
        
        tenant.refresh_from_db()
        assert tenant.is_premium is True

    def test_process_webhook_failed(self):
        from payments.services import PaymentService
        subscription = SubscriptionFactory(status=SubscriptionStatus.PENDING)
        payment = PaymentFactory(subscription=subscription, order_id="order_failed", status=PaymentStatus.CREATED)
        
        payload = {
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail1",
                        "order_id": "order_failed",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Payment failed by bank"
                    }
                }
            }
        }
        
        webhook = WebhookEventFactory(event_id="evt_fail1", event_type="payment.failed", payload=payload)
        
        service = PaymentService()
        service.process_webhook(webhook)
        
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.FAILED
        assert payment.error_code == "BAD_REQUEST_ERROR"
        
        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.FAILED
