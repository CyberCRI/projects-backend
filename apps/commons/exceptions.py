from enum import Enum

from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler


class ExceptionType(Enum):
    VALIDATION = "validation"
    AUTHENTHICATION = "authentication"
    PERMISSION = "permission"
    TECHNICAL = "technical"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


def get_exception_type(exc: Exception) -> str:
    """
    Get the type of exception.

    The order of the exception_types is important because some exceptions are
    subclasses of others
    """
    exception_types = [
        (ValidationError, ExceptionType.VALIDATION.value),
        (NotAuthenticated, ExceptionType.AUTHENTHICATION.value),
        (AuthenticationFailed, ExceptionType.AUTHENTHICATION.value),
        (PermissionDenied, ExceptionType.PERMISSION.value),
        (APIException, ExceptionType.TECHNICAL.value),
        (Http404, ExceptionType.NOT_FOUND.value),
    ]
    for exception_class, exception_type in exception_types:
        if isinstance(exc, exception_class):
            return exception_type
    return ExceptionType.UNKNOWN.value


def projects_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        exception_type = get_exception_type(exc)
        if exception_type == ExceptionType.VALIDATION.value:
            response.data = {
                "type": exception_type,
                "errors": response.data,
            }
        else:
            response.data = {
                "type": exception_type,
                **response.data,
            }
    return response
