import logging
import uuid
import secrets
from django.template.loader import render_to_string
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import F
from django.db import transaction
from django.core.management import call_command
from datetime import timedelta
from recipes.models import Recipe, RecipeIngredient, RecipePicture
from common.constants import (
    OTP_TIMEOUT,
    OTP_EXPIRY_MINUTES,
)
from .utils import set_reset_token, hash_otp, set_user_otp
from .models import User

logger = logging.getLogger(__name__)


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

    set_user_otp(to_email, otp, prefix="login_otp", timeout=OTP_TIMEOUT)

    context = {
        "otp": otp,
        "expires_in": OTP_EXPIRY_MINUTES,
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
    deleted_at_dt = timezone.datetime.fromisoformat(deleted_at)

    with transaction.atomic():
        Recipe.objects.filter(user_id=user_id, is_active=True).update(
            is_active=False, deleted_at=deleted_at_dt
        )

        RecipeIngredient.objects.filter(recipe__user_id=user_id, is_active=True).update(
            is_active=False, deleted_at=deleted_at_dt
        )
        RecipePicture.objects.filter(recipe__user_id=user_id, is_active=True).update(
            is_active=False, deleted_at=deleted_at_dt
        )

    logger.info(
        f"All active recipes and related resources deactivated for user: {user_id}"
    )


@shared_task
def restore_user_resources(user_id, deleted_at):
    if not deleted_at:
        return

    deleted_at_dt = timezone.datetime.fromisoformat(deleted_at)

    with transaction.atomic():
        Recipe.objects.filter(
            user_id=user_id, is_active=False, deleted_at=deleted_at_dt
        ).update(is_active=True, deleted_at=None)

        RecipeIngredient.objects.filter(
            recipe__user_id=user_id, is_active=False, deleted_at=deleted_at_dt
        ).update(is_active=True, deleted_at=None)

        RecipePicture.objects.filter(
            recipe__user_id=user_id, is_active=False, deleted_at=deleted_at_dt
        ).update(is_active=True, deleted_at=None)

    logger.info(f"Recipes and related resources restored for user: {user_id}")


@shared_task
def flush_expired_tokens():
    call_command("flushexpiredtokens")
    logger.info("Expired tokens flushed from blacklist")
