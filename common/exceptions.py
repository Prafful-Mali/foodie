from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse


def custom_api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "errors": (
                    exc.message_dict if hasattr(exc, "message_dict") else exc.messages
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {"errors": {"detail": str(exc)}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(response.data, dict):
        response.data = {"errors": response.data}
    elif isinstance(response.data, list):
        response.data = {"errors": {"detail": response.data}}

    return response


def custom_404_handler(request, exception):
    return JsonResponse(
        {"errors": {"detail": "The requested resource does not exist."}},
        status=404,
    )
