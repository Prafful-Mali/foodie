# from rest_framework_simplejwt.authentication import JWTAuthentication
# from rest_framework.exceptions import AuthenticationFailed


# class TenantMiddleware:
#     """
#     Middleware to automatically attach tenant to request object.
#     Handles both session-based and JWT authentication.
#     """
#     def __init__(self, get_response):
#         self.get_response = get_response
#         self.jwt_authenticator = JWTAuthentication()

#     def __call__(self, request):
#         # Try to authenticate via JWT if Authorization header is present
#         if request.path.startswith('/api/') and 'Authorization' in request.headers:
#             try:
#                 auth_result = self.jwt_authenticator.authenticate(request)
#                 if auth_result is not None:
#                     request.user, _ = auth_result
#             except (AuthenticationFailed, Exception):
#                 pass  # Let DRF handle authentication errors

#         # Add tenant to request if user is authenticated
#         if hasattr(request, 'user') and request.user.is_authenticated:
#             request.tenant = getattr(request.user, 'tenant', None)
#         else:
#             request.tenant = None

#         response = self.get_response(request)
#         return response

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
