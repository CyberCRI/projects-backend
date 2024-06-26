from enum import Enum

from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
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


class MissingUrlArgument(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Missing required URL argument.")
    default_code = "missing_url_argument"

    def __init__(self, view_name: str, kwarg_name: str):
        detail = _(
            f"Missing required URL argument '{kwarg_name}' in view '{view_name}'."
        )
        super().__init__(detail=detail)


class MissingSerializerContext(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Missing serializer context.")
    default_code = "missing_serializer_context"

    def __init__(self, serializer_name: str, parameter_name: str):
        detail = _(
            f"Missing required '{parameter_name}' parameter in context for '{serializer_name}'."
        )
        super().__init__(detail=detail)
