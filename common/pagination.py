from rest_framework.pagination import PageNumberPagination
from .constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_MAX_PAGE_SIZE,
    DEFAULT_PAGE_SIZE_QUERY_PARAM,
)


class DefaultPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = DEFAULT_PAGE_SIZE_QUERY_PARAM
    max_page_size = DEFAULT_MAX_PAGE_SIZE
