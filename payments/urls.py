from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TenantOrderViewSet,
    SubscriptionViewSet,
    PaymentViewSet,
    WebhookViewSet,
    VerifyPaymentView,
    RazorpayWebhookView,
    subscribe_page,
    payment_callback,
)

router = DefaultRouter()
router.register(r"orders", TenantOrderViewSet, basename="order")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"webhooks", WebhookViewSet, basename="webhook")

urlpatterns = [
    path("api/v1/payments/verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path(
        "api/v1/webhook/razorpay/",
        RazorpayWebhookView.as_view(),
        name="razorpay-webhook",
    ),
    path("subscribe/", subscribe_page, name="subscribe-page"),
    path("payment/callback/", payment_callback, name="payment-callback"),
    path("api/v1/", include(router.urls)),
]
