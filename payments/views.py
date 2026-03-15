import logging
import uuid
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from common.pagination import DefaultPagination
from tenants.permissions import IsSuperAdmin
from .models import Subscription, Payment, WebhookEvent
from .serializers import (
    SubscriptionSerializer,
    VerifyPaymentSerializer,
    PaymentSerializer,
    WebhookEventSerializer,
)
from .permissions import IsTenantAdmin
from .services import PaymentService
from .tasks import process_webhook_task

logger = logging.getLogger(__name__)


class TenantOrderViewSet(viewsets.ViewSet):
    def get_permissions(self):
        return [IsTenantAdmin()]

    def list(self, request):
        qs = Subscription.objects.filter(tenant=request.tenant, is_active=True)
        paginator = DefaultPagination()
        paginated = paginator.paginate_queryset(qs, request)
        serializer = SubscriptionSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        service = PaymentService()

        try:
            subscription, payment, order = service.create_subscription(
                tenant=request.tenant, user=request.user
            )

        except ValidationError as e:
            return Response(
                {"errors": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "subscription_id": str(subscription.id),
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="status")
    def check_status(self, request):
        subscription = (
            Subscription.objects.filter(tenant=request.tenant, is_active=True)
            .order_by("-created_at")
            .first()
        )

        if not subscription:
            return Response(
                {"status": "no_subscription"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "status": subscription.status,
                "is_premium": request.tenant.is_premium,
                "activated_at": subscription.activated_at,
            },
            status=status.HTTP_200_OK,
        )


class VerifyPaymentView(APIView):
    permission_classes = [IsTenantAdmin]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment = get_object_or_404(
            Payment,
            order_id=data["razorpay_order_id"],
            tenant=request.tenant,
        )

        service = PaymentService()
        is_valid = service.verify_payment_signature(
            payment=payment,
            payment_id=data["razorpay_payment_id"],
            signature=data["razorpay_signature"],
        )

        if not is_valid:
            return Response(
                {"errors": {"detail": "Signature verification failed"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "verified",
                "payment_status": payment.status,
                "subscription_status": payment.subscription.status,
                "is_premium": payment.tenant.is_premium,
                "message": "Payment verified. Awaiting webhook confirmation.",
            },
            status=status.HTTP_200_OK,
        )


class RazorpayWebhookView(APIView):
    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature")

        if not signature:
            logger.error("Webhook without signature")
            return Response(
                {"status": "error", "message": "Missing signature"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = PaymentService()

        if not service.verify_webhook_signature(
            request.body.decode("utf-8"), signature
        ):
            logger.error("Invalid webhook signature")
            return Response(
                {"status": "error", "message": "Invalid signature"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = request.data
            event_id = payload.get("id") or f"{payload.get('event')}-{uuid.uuid4()}"
            event_type = payload.get("event")

            webhook, created = service.store_webhook(
                event_id=event_id, event_type=event_type, payload=payload
            )

            if not created:
                logger.info(f"Duplicate webhook {event_id}")
                return Response({"status": "duplicate"}, status=status.HTTP_200_OK)

            process_webhook_task.delay(str(webhook.id))

            logger.info(f"Webhook {event_id} queued")
            return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            return Response(
                {"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def subscribe_page(request):
    return render(
        request,
        "payments/subscribe.html",
        {"razorpay_key_id": settings.RAZORPAY_KEY_ID},
    )


@csrf_exempt
def payment_callback(request):
    data = request.POST if request.method == "POST" else request.GET

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    error_desc = data.get("error[description]")

    if razorpay_order_id and razorpay_payment_id and razorpay_signature:
        payment = Payment.objects.filter(order_id=razorpay_order_id).first()
        if not payment:
            return redirect("/subscribe/?status=failed&reason=order_not_found")

        service = PaymentService()
        is_valid = service.verify_payment_signature(
            payment=payment,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
        )

        if is_valid:
            return redirect("/subscribe/?status=success")
        else:
            return redirect("/subscribe/?status=failed")

    reason = error_desc or "payment_failed"
    return redirect(f"/subscribe/?status=failed&reason={reason}")


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    pagination_class = DefaultPagination


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    pagination_class = DefaultPagination


class WebhookViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
    pagination_class = DefaultPagination
