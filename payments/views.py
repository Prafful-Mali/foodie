import logging
import razorpay
import uuid
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from common.pagination import DefaultPagination
from common.constants import LIFETIME_AMOUNT_PAISE
from common.enums import SubscriptionStatus, PaymentStatus
from .models import Subscription, Payment, WebhookEvent
from .serializers import SubscriptionSerializer, VerifyPaymentSerializer
from .permissions import IsTenantAdmin

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
        except Exception:
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
            payment.payment_id = data["razorpay_payment_id"]
            payment.status = PaymentStatus.CAPTURED
            payment.captured = True
            payment.save()

            subscription = payment.subscription
            subscription.status = SubscriptionStatus.PAID
            subscription.activated_at = subscription.activated_at or payment.created_at
            subscription.save()

            tenant = subscription.tenant
            tenant.is_premium = True
            tenant.save(update_fields=["is_premium"])

        return Response({"status": "verified"}, status=status.HTTP_200_OK)


class RazorpayWebhookView(APIView):
    def post(self, request):
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
            payment_id = payment_entity.get("id")

            if not order_id:
                return Response(status=200)

            payment = Payment.objects.filter(order_id=order_id).first()
            if not payment:
                return Response(status=200)

            webhook_event, created = WebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={
                    "tenant": payment.tenant,
                    "payment": payment,
                    "event_type": event_type,
                    "payload": payload,
                },
            )

            if not created:
                return Response(status=200)

            with transaction.atomic():
                if event_type == "payment.captured":
                    payment.payment_id = payment_id
                    payment.status = PaymentStatus.CAPTURED
                    payment.captured = True
                    payment.method = payment_entity.get("method")
                    payment.email = payment_entity.get("email")
                    payment.contact = payment_entity.get("contact")
                    payment.fee = payment_entity.get("fee")
                    payment.tax = payment_entity.get("tax")
                    payment.save()

                    subscription = payment.subscription
                    subscription.status = SubscriptionStatus.PAID
                    subscription.activated_at = (
                        subscription.activated_at or payment.created_at
                    )
                    subscription.save()

                    tenant = subscription.tenant
                    tenant.is_premium = True
                    tenant.save(update_fields=["is_premium"])

                elif event_type == "payment.failed":
                    payment.status = PaymentStatus.FAILED
                    payment.error_code = payment_entity.get("error_code")
                    payment.error_description = payment_entity.get("error_description")
                    payment.save()

                    subscription = payment.subscription
                    subscription.status = SubscriptionStatus.FAILED
                    subscription.save()

            return Response(status=200)

        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            return Response(status=200)


def subscribe_page(request):
    return render(
        request,
        "payments/subscribe.html",
        {
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        },
    )
