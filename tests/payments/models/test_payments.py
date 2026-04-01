import pytest
from tests.factories.payments import (
    SubscriptionFactory,
    PaymentFactory,
    WebhookEventFactory,
)
from common.enums import SubscriptionStatus, PaymentStatus


@pytest.mark.django_db
class TestSubscriptionModel:
    def test_subscription_creation(self):
        subscription = SubscriptionFactory(amount=50000)
        assert subscription.amount == 50000
        assert subscription.status == SubscriptionStatus.PENDING
        assert (
            str(subscription)
            == f"Subscription({subscription.tenant.name}, {subscription.status})"
        )


@pytest.mark.django_db
class TestPaymentModel:
    def test_payment_creation(self):
        payment = PaymentFactory(amount=50000, order_id="order_123")
        assert payment.amount == 50000
        assert payment.order_id == "order_123"
        assert payment.status == PaymentStatus.CREATED
        assert str(payment) == f"Payment(order_123, {PaymentStatus.CREATED})"


@pytest.mark.django_db
class TestWebhookEventModel:
    def test_webhook_event_creation(self):
        event = WebhookEventFactory(event_type="payment.captured", event_id="evt_abc")
        assert event.event_type == "payment.captured"
        assert event.event_id == "evt_abc"
        assert str(event) == "payment.captured - evt_abc"
