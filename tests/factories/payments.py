import factory
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory
from payments.models import Subscription, Payment, WebhookEvent
from common.enums import SubscriptionStatus, PaymentStatus
from django.utils import timezone
from common.constants import LIFETIME_AMOUNT_PAISE


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    tenant = factory.SubFactory(TenantFactory)
    created_by = factory.SubFactory(UserFactory)
    amount = LIFETIME_AMOUNT_PAISE
    status = SubscriptionStatus.PENDING
    is_active = True
    activated_at = None


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    tenant = factory.SubFactory(TenantFactory)
    subscription = factory.SubFactory(SubscriptionFactory)
    user = factory.SubFactory(UserFactory)

    order_id = factory.Sequence(lambda n: f"order_{n}")
    payment_id = factory.Sequence(lambda n: f"pay_{n}")
    amount = LIFETIME_AMOUNT_PAISE
    currency = "INR"
    status = PaymentStatus.CREATED
    captured = False
    is_active = True


class WebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    event_id = factory.Sequence(lambda n: f"evt_{n}")
    event_type = "payment.captured"
    payload = {}
    processed = False
