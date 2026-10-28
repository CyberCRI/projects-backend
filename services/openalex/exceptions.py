from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

# Technical errors


class OpenAlexAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("OpenAlex API error")
    default_code = "openalex_api_error"

    def __init__(self, status_code: int | None = None):
        detail = (
            _("OpenAlex API returned {status_code}").format(status_code=status_code)
            if status_code
            else self.default_detail
        )
        super().__init__(detail=detail)
