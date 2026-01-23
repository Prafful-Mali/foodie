from django.core.cache import cache
import hashlib

from common.constants import RESET_TOKEN_TTL


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_reset_token(token: str, user_id: str):
    hashed_token = hash_token(token)
    cache.set(f"pwd-reset:{hashed_token}", str(user_id), timeout=RESET_TOKEN_TTL)


def get_user_id_from_token(token: str):
    hashed_token = hash_token(token)
    return cache.get(f"pwd-reset:{hashed_token}")


def delete_reset_token(token: str):
    hashed_token = hash_token(token)
    cache.delete(f"pwd-reset:{hashed_token}")
