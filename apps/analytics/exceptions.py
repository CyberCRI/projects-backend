from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ValidationError


class UnknownPublicationStatusError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Unknown publication status")
    default_code = "unknown_publication_status_error"

    def __init__(self, publication_status: Optional[str] = None):
        detail = (
            _("Unknown publication status '{publication_status}'").format(
                publication_status=publication_status
            )
            if publication_status
            else self.default_detail
        )
        super().__init__(detail=detail)
