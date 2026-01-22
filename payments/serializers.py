from rest_framework import serializers
from .models import Subscription, Payment


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id",
            "razorpay_order_id",
            "amount",
            "status",
            "is_active",
            "activated_at",
            "created_at",
        ]
        read_only_fields = fields


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = fields
