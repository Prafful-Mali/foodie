from django.core.cache import cache
import hashlib

from common.constants import RESET_TOKEN_TTL, OTP_TIMEOUT, OTP_LIMIT_TIMEOUT


def hash_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def hash_otp(otp: str):
    return hash_token(otp)


def set_user_otp(email: str, otp: str, prefix: str = "otp", timeout: int = OTP_TIMEOUT):
    cache.set(f"{prefix}:{email}", hash_otp(otp), timeout=timeout)


def get_user_otp(email: str, prefix: str = "otp"):
    return cache.get(f"{prefix}:{email}")


def delete_user_otp(email: str, prefix: str = "otp"):
    cache.delete(f"{prefix}:{email}")


def is_otp_rate_limited(
    email: str, prefix: str = "otp", timeout: int = OTP_LIMIT_TIMEOUT
):
    key = f"{prefix}_limit:{email}"
    return not cache.add(key, True, timeout=timeout)


def set_reset_token(token: str, user_id: str):
    hashed_token = hash_token(token)
    cache.set(f"pwd-reset:{hashed_token}", str(user_id), timeout=RESET_TOKEN_TTL)


def get_user_id_from_token(token: str):
    hashed_token = hash_token(token)
    return cache.get(f"pwd-reset:{hashed_token}")


def delete_reset_token(token: str):
    hashed_token = hash_token(token)
    cache.delete(f"pwd-reset:{hashed_token}")
