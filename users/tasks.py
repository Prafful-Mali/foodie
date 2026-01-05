from django.conf import settings
from celery import shared_task
from django.core.mail import send_mail
from .utils import generate_temp_password
from .models import User


@shared_task
def send_temp_password_email(to_email):
    user = User.objects.filter(email=to_email).first()
    if not user:
        return

    password = generate_temp_password()

    user.set_password(password)
    user.save()

    message = f"""Hello,

We received a request to generate a temporary password for your account.

Your temporary password is:

{password}

Please use this password to sign in, and change it immediately after logging in for security reasons.

If you did not request this change, please contact our support team.

Thank you,
Support Team
"""

    send_mail(
        subject="Your Temporary Password",
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[to_email],
    )

    return password
