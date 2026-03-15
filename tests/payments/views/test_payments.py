import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from tests.factories.payments import SubscriptionFactory, PaymentFactory
from common.enums import SubscriptionStatus, PaymentStatus
from payments.models import Subscription, Payment

from common.constants import LIFETIME_AMOUNT_PAISE

@pytest.mark.django_db
class TestPaymentIntegration:

    @patch('razorpay.Client')
    def test_create_order_as_tenant_admin(self, mock_razorpay, admin_client, tenant, user):
        # Mocking Razorpay client
        mock_client_instance = MagicMock()
        mock_razorpay.return_value = mock_client_instance
        mock_client_instance.order.create.return_value = {
            "id": "order_test_123",
            "amount": LIFETIME_AMOUNT_PAISE,
            "currency": "INR",
        }

        response = admin_client.post(reverse("order-list"))
        
        assert response.status_code == 201
        assert response.data["order_id"] == "order_test_123"
        
        assert Subscription.objects.filter(tenant=tenant).exists()
        assert Payment.objects.filter(tenant=tenant, order_id="order_test_123").exists()

    @patch('razorpay.Client')
    def test_create_order_when_already_active(self, mock_razorpay, admin_client, tenant):
        # Setup an active paid subscription
        SubscriptionFactory(tenant=tenant, status=SubscriptionStatus.PAID)
        
        response = admin_client.post(reverse("order-list"))
        assert response.status_code == 400
        assert "already exists" in response.data["errors"]["detail"]

    def test_create_order_as_regular_user(self, authenticated_client):
        response = authenticated_client.post(reverse("order-list"))
        assert response.status_code == 403

    def test_check_status_no_subscription(self, admin_client):
        response = admin_client.get(reverse("order-check-status"))
        assert response.status_code == 404

    def test_list_orders_as_tenant_admin(self, admin_client, tenant):
        SubscriptionFactory(tenant=tenant)
        SubscriptionFactory(tenant=tenant, is_active=False)
        # Create for another tenant to test isolation
        SubscriptionFactory()
        
        response = admin_client.get(reverse("order-list"))
        assert response.status_code == 200
        # Should only return the active subscription for this tenant
        assert len(response.data["results"]) == 1

    def test_check_status_with_subscription(self, admin_client, tenant):
        SubscriptionFactory(tenant=tenant, status=SubscriptionStatus.PENDING)
        response = admin_client.get(reverse("order-check-status"))
        assert response.status_code == 200
        assert response.data["status"] == SubscriptionStatus.PENDING

    @patch('razorpay.Client')
    def test_verify_payment_success(self, mock_razorpay, admin_client, tenant):
        mock_client_instance = MagicMock()
        mock_razorpay.return_value = mock_client_instance
        # Don't raise error, means signature is valid
        mock_client_instance.utility.verify_payment_signature.return_value = None

        subscription = SubscriptionFactory(tenant=tenant)
        payment = PaymentFactory(
            tenant=tenant, 
            subscription=subscription, 
            order_id="order_123",
            status=PaymentStatus.CREATED
        )

        payload = {
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "valid_signature"
        }

        response = admin_client.post(reverse("payment-verify"), data=payload)
        
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.VERIFIED
        assert payment.payment_id == "pay_123"
        assert payment.verified_at is not None

    @patch('razorpay.Client')
    def test_verify_payment_invalid_signature(self, mock_razorpay, admin_client, tenant):
        import razorpay
        mock_client_instance = MagicMock()
        mock_razorpay.return_value = mock_client_instance
        mock_client_instance.utility.verify_payment_signature.side_effect = razorpay.errors.SignatureVerificationError("Invalid signature")

        payment = PaymentFactory(tenant=tenant, order_id="order_invalid")

        payload = {
            "razorpay_order_id": "order_invalid",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "invalid_signature"
        }

        response = admin_client.post(reverse("payment-verify"), data=payload)
        assert response.status_code == 400
        assert "failed" in response.data["errors"]["detail"]


@pytest.mark.django_db
class TestAdminViewsIntegration:

    def test_list_subscriptions_superadmin(self, superadmin_client):
        SubscriptionFactory.create_batch(3)
        response = superadmin_client.get(reverse("subscription-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) == 3

    def test_list_subscriptions_normal_admin(self, admin_client):
        response = admin_client.get(reverse("subscription-list"))
        assert response.status_code == 403

    def test_list_payments_superadmin(self, superadmin_client):
        PaymentFactory.create_batch(2)
        response = superadmin_client.get(reverse("payment-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) == 2
