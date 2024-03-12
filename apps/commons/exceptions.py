from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler


def projects_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        exception_types = [
            (ValidationError, "validation"),
            (NotAuthenticated, "authentication"),
            (AuthenticationFailed, "authentication"),
            (PermissionDenied, "permission"),
            (APIException, "technical"),
        ]
        for exception_class, exception_type in exception_types:
            if isinstance(exc, exception_class):
                response.data = {
                    "type": exception_type,
                    "errors": response.data,
                }
                return response
        response.data = {
            "type": "unknown",
            "errors": response.data,
        }
    return response
