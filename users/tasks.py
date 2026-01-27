import logging
import uuid
import secrets
from django.core.cache import cache
from django.conf import settings
from django.template.loader import render_to_string
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import F
from django.core.management import call_command
from datetime import timedelta
from .utils import set_reset_token, hash_otp
from .models import User

logger = logging.getLogger(__name__)


@shared_task
def send_verification_email(to_email):
    otp = f"{secrets.randbelow(1000000):06d}"
    cache.set(f"otp:{to_email}", hash_otp(otp), timeout=300)

    context = {
        "otp": otp,
        "expires_in": 5,
    }

    html_content = render_to_string("emails/verification_otp.html", context)
    text_content = f"Your OTP is {otp}. It expires in 5 minutes."

    send_mail(
        subject="Your OTP for verification",
        message=text_content,
        from_email=None,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )
    logger.info(f"Verification email sent to: {to_email}")

    return "OTP sent"




@shared_task
def cleanup_soft_deleted_users():
    threshold = timezone.now() - timedelta(days=7)
    User.objects.filter(
        is_active=False, deleted_at__lt=threshold, deleted_by=F("id")
    ).delete()
    logger.info("Cleanup of self-deleted users completed")


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
        from_email=None,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )


@shared_task
def send_setup_password_email(to_email, base_url):
    user = User.objects.filter(email=to_email).first()
    if not user:
        return

    token = uuid.uuid4().hex
    set_reset_token(token, user.id)

    setup_link = f"{base_url}/api/v1/setup-password/{token}/"

    context = {
        "user": user,
        "setup_link": setup_link,
    }

    html_content = render_to_string("emails/setup_password.html", context)
    text_content = f"Set your password using this link:\n{setup_link}"

    send_mail(
        subject="Set your password",
        message=text_content,
        from_email=None,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )


@shared_task
def send_login_otp_email(to_email):

    otp = f"{secrets.randbelow(1000000):06d}"

    cache.set(f"login_otp:{to_email}", hash_otp(otp), timeout=300)

    context = {
        "otp": otp,
        "expires_in": 5,
    }

    html_content = render_to_string("emails/login_otp.html", context)
    text_content = f"Your login OTP is {otp}. It expires in 5 minutes."

    send_mail(
        subject="Your Login OTP",
        message=text_content,
        from_email=None,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )
    logger.info(f"Login OTP email sent to: {to_email}")

    return "Login OTP sent"


@shared_task
def send_invite_email(to_email, base_url, tenant_name):
    token = uuid.uuid4().hex

    user = User.objects.get(email=to_email)
    set_reset_token(token, user.id)

    invite_link = f"{base_url}/api/v1/invite/accept/{token}/"

    context = {
        "invite_link": invite_link,
        "tenant_name": tenant_name,
    }

    html_content = render_to_string("emails/invite_user.html", context)
    text_content = (
        f"You've been invited to join {tenant_name}. "
        f"Accept the invitation using this link:\n{invite_link}"
    )

    send_mail(
        subject=f"Invitation to join {tenant_name}",
        message=text_content,
        from_email=None,
        recipient_list=[to_email],
        html_message=html_content,
        fail_silently=False,
    )

    logger.info(f"Invite email sent to: {to_email} for tenant: {tenant_name}")


@shared_task
def deactivate_user_resources(user_id, deleted_at):
    from recipes.models import Recipe

    Recipe.objects.filter(user_id=user_id, is_active=True).update(
        is_active=False, deleted_at=deleted_at
    )
    logger.info(f"All active recipes deactivated for user: {user_id}")


@shared_task
def restore_user_resources(user_id, deleted_at):
    from recipes.models import Recipe

    if not deleted_at:
        return

    # Only restore recipes that were deleted at the exact same time as the user
    # to avoid restoring recipes the user had manually deleted earlier.
    Recipe.objects.filter(
        user_id=user_id, is_active=False, deleted_at=deleted_at
    ).update(is_active=True, deleted_at=None)
    logger.info(f"Synchronized recipes restored for user: {user_id}")


@shared_task
def flush_expired_tokens():
    call_command("flushexpiredtokens")
    logger.info("Expired tokens flushed from blacklist")
