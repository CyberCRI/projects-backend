from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

# Technical errors


class WikibaseAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Wikipedia API error")
    default_code = "wikibase_api_error"

    def __init__(self, status_code: Optional[int] = None):
        detail = (
            _(f"Wikipedia API returned {status_code}")
            if status_code
            else self.default_detail
        )
        super().__init__(detail=detail)


class UnsupportedWikipediaLanguageError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Language is not supported")
    default_code = "unsupported_wikipedia_language_error"

    def __init__(self, language: Optional[str] = None):
        detail = (
            _(f"Language {language} is not supported")
            if language
            else self.default_detail
        )
        super().__init__(detail=detail)
