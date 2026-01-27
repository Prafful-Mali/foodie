from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SubscriptionViewSet,
    VerifyPaymentView,
    RazorpayWebhookView,
    subscribe_page,
)

router = DefaultRouter()
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("api/v1/payments/verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("api/v1/webhook/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    path("subscribe/", subscribe_page, name="subscribe-page"),
    path("api/v1/", include(router.urls)),
]