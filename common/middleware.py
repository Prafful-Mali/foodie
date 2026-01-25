import time
import logging
import json
import uuid
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


class RequestLoggingMiddleware:
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("django.request")

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id

        start_time = time.time()

        try:
            response = self.get_response(request)
        except Exception:
            duration = (time.time() - start_time) * 1000

            fake_response = type("Response", (), {"status_code": 500})()

            self.log_request(request, fake_response, duration)

            raise

        duration = (time.time() - start_time) * 1000
        self.log_request(request, response, duration)

        if not response.has_header("X-Request-ID"):
            response["X-Request-ID"] = request_id

        return response

    def log_request(self, request, response, duration):
        user = getattr(request, "user", None)
        tenant = getattr(request, "tenant", None)

        user_id = str(user.id) if user and user.is_authenticated else "anonymous"
        tenant_id = str(tenant.id) if tenant else "none"

        log_data = {
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration, 2),
            "request_id": request.request_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "client_ip": self.get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }

        log_json = json.dumps(log_data)

        if response.status_code >= 500:
            self.logger.error(log_json)
        elif response.status_code >= 400:
            self.logger.warning(log_json)
        else:
            self.logger.info(log_json)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
