from django.utils.crypto import get_random_string
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def generate_temp_password(user=None, length=12):
    allowed_chars = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+"
    )

    while True:
        password = get_random_string(length, allowed_chars)
        try:
            validate_password(password, user=user)
            return password
        except ValidationError:
            continue
