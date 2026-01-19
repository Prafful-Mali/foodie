from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class TenantMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        request.tenant = None

        if "Authorization" in request.headers:
            try:
                auth_result = self.jwt_auth.authenticate(request)
                if auth_result is not None:
                    user, _ = auth_result
                    request.user = user
                    request.tenant = getattr(user, "tenant", None)
            except AuthenticationFailed:
                pass

        if not hasattr(request, "user"):
            request.user = AnonymousUser()

        return self.get_response(request)
