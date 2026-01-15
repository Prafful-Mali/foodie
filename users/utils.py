from django.core.cache import cache

RESET_TOKEN_TTL = 15 * 60


def set_reset_token(token: str, user_id: str):
    cache.set(f"pwd-reset:{token}", str(user_id), timeout=RESET_TOKEN_TTL)


def get_user_id_from_token(token: str):
    return cache.get(f"pwd-reset:{token}")


def delete_reset_token(token: str):
    cache.delete(f"pwd-reset:{token}")
