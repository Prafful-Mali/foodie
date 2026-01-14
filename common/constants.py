from datetime import timedelta

ACCESS_TOKEN_LIFETIME = timedelta(minutes=5)
REFRESH_TOKEN_LIFETIME = timedelta(days=1)

DEFAULT_PAGE_SIZE = 5
DEFAULT_MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE_QUERY_PARAM = "page_size"
