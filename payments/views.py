import logging
import razorpay
import uuid
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from common.pagination import DefaultPagination
from common.constants import LIFETIME_AMOUNT_PAISE
from common.enums import SubscriptionStatus, PaymentStatus
from .models import Subscription, Payment, WebhookEvent
from .serializers import (
    SubscriptionSerializer,
    VerifyPaymentSerializer,
    PaymentSerializer,
)
from .permissions import IsTenantAdmin
from .tasks import process_webhook_event

logger = logging.getLogger(__name__)

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class SubscriptionViewSet(viewsets.ViewSet):
    def get_permissions(self):
        return [IsTenantAdmin()]

    def list(self, request):
        tenant = request.tenant
        qs = Subscription.objects.filter(tenant=tenant, is_active=True)

        paginator = DefaultPagination()
        paginated = paginator.paginate_queryset(qs, request)
        serializer = SubscriptionSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        tenant = request.tenant
        user = request.user

        active_subscription = Subscription.objects.filter(
            tenant=tenant, status=SubscriptionStatus.PAID, is_active=True
        ).first()

        if active_subscription:
            return Response(
                {"errors": {"detail": "An active subscription already exists."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = LIFETIME_AMOUNT_PAISE

        with transaction.atomic():
            subscription = Subscription.objects.create(
                tenant=tenant,
                created_by=user,
                amount=amount,
                status=SubscriptionStatus.PENDING,
            )

            order = razorpay_client.order.create(
                {
                    "amount": amount,
                    "currency": "INR",
                    "payment_capture": 1,
                }
            )

            Payment.objects.create(
                tenant=tenant,
                subscription=subscription,
                user=user,
                order_id=order["id"],
                amount=amount,
                status=PaymentStatus.CREATED,
            )

        return Response(
            {
                "order_id": order["id"],
                "amount": amount,
                "currency": "INR",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="status")
    def check_status(self, request):
        tenant = request.tenant

        subscription = (
            Subscription.objects.filter(tenant=tenant, is_active=True)
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
                "is_premium": tenant.is_premium,
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

        try:
            razorpay_client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": data["razorpay_order_id"],
                    "razorpay_payment_id": data["razorpay_payment_id"],
                    "razorpay_signature": data["razorpay_signature"],
                }
            )
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return Response(
                {"errors": {"detail": "Signature verification failed"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = get_object_or_404(
            Payment,
            order_id=data["razorpay_order_id"],
            tenant=request.tenant,
        )

        with transaction.atomic():
            if payment.status == PaymentStatus.CREATED:
                payment.payment_id = data["razorpay_payment_id"]
                payment.status = PaymentStatus.VERIFIED
                payment.save(update_fields=["payment_id", "status", "updated_at"])

        subscription = payment.subscription
        
        return Response(
            {
                "status": "verified",
                "payment_status": payment.status,
                "subscription_status": subscription.status,
                "is_premium": subscription.tenant.is_premium,
                "message": "Signature verified. Awaiting webhook confirmation."
            },
            status=status.HTTP_200_OK
        )

class RazorpayWebhookView(APIView):
    def post(self, request):
        webhook_signature = request.headers.get("X-Razorpay-Signature")
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

        if not webhook_signature:
            logger.error("Webhook received without signature")
            return Response(
                {"status": "error", "message": "Missing signature"}, 
                status=400
            )

        try:
            razorpay_client.utility.verify_webhook_signature(
                body=request.body.decode('utf-8'),
                signature=webhook_signature,
                secret=webhook_secret,
            )
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return Response(
                {"status": "error", "message": "Invalid signature"}, 
                status=400
            )

        try:
            payload = request.data
            event_type = payload.get("event")
            event_id = payload.get("id")

            if not event_id:
                event_id = f"{event_type}-{uuid.uuid4()}"

            payment_entity = (
                payload.get("payload", {}).get("payment", {}).get("entity", {})
            )
            order_id = payment_entity.get("order_id")

            if not order_id:
                logger.warning(f"Webhook {event_id} has no order_id, ignoring")
                return Response({"status": "ignored"}, status=200)

            payment = Payment.objects.filter(order_id=order_id).first()
            if not payment:
                logger.warning(f"Payment not found for order_id {order_id}")
                return Response({"status": "payment_not_found"}, status=200)

            webhook_event, created = WebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={
                    "tenant": payment.tenant,
                    "payment": payment,
                    "event_type": event_type,
                    "payload": payload,
                    "processed": False,
                },
            )

            if not created:
                logger.info(f"Webhook {event_id} already exists, skipping")
                return Response({"status": "duplicate"}, status=200)

            process_webhook_event.delay(str(webhook_event.id))

            logger.info(f"Webhook {event_id} queued for processing")
            return Response({"status": "queued"}, status=200)

        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            return Response({"status": "error"}, status=200)

def subscribe_page(request):
    return render(
        request,
        "payments/subscribe.html",
        {
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        },
    )
