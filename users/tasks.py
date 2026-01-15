import uuid
import secrets
from django.core.cache import cache
from django.conf import settings
from django.template.loader import render_to_string
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .utils import set_reset_token
from .models import User


@shared_task
def send_verification_email(to_email):
    otp = f"{secrets.randbelow(1000000):06d}"
    cache.set(f"otp:{to_email}", otp, timeout=300)

    context = {
        "otp": otp,
        "expires_in": 5,
    }

    html_content = render_to_string("emails/verification_otp.html", context)
    text_content = f"Your OTP is {otp}. It expires in 5 minutes."

    send_mail(
        subject="Your OTP for verification",
        message=text_content,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )

    return "OTP sent"


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def hard_delete_user(self, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return "User already deleted"

    if not user.is_active and user.deleted_at:
        user.delete()
        return f"User {user_id} hard deleted"

    return f"User {user_id} was restored; skipping hard delete"


@shared_task
def cleanup_soft_deleted_users():
    threshold = timezone.now() - timedelta(days=90)
    User.objects.filter(is_active=False, deleted_at__lt=threshold).delete()


@shared_task
def send_reset_password_email(to_email, base_url):
    user = User.objects.filter(email=to_email).first()
    if not user:
        return

    token = uuid.uuid4().hex
    set_reset_token(token, user.id)

    reset_link = f"{base_url}/api/v1/reset-password/{token}/"

    context = {
        "user": user,
        "reset_link": reset_link,
    }

    html_content = render_to_string("emails/reset_password.html", context)
    text_content = f"Reset your password using this link:\n{reset_link}"

    send_mail(
        subject="Reset your password",
        message=text_content,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )
