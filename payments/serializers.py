from rest_framework import serializers
from .models import Subscription, Payment


class SubscriptionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "amount",
            "status",
            "is_active",
            "activated_at",
            "created_at",
            "created_by_email",
        ]
        read_only_fields = fields


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_id",
            "payment_id",
            "amount",
            "currency",
            "status",
            "method",
            "email",
            "contact",
            "captured",
            "verified_at",
            "captured_at",
            "created_at",
            "user_email",
        ]
        read_only_fields = fields