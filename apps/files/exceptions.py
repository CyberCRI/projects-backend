from typing import Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

# Validation errors


class DuplicatedFileError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "The file you are trying to upload is already attached to this project"
    )
    default_code = "duplicated_file_error"


class DuplicatedOrganizationFileError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "The file you are trying to upload is already attached to this organization"
    )
    default_code = "duplicated_organization_file_error"


class DuplicatedLinkError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "The link you are trying to attach is already attached to this project"
    )
    default_code = "duplicated_link_error"


class FileTooLargeError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "File too large. Size should not exceed {max_file_size} MB"
    ).format(max_file_size=settings.MAX_FILE_SIZE)
    default_code = "file_too_large_error"


class ChangeFileProjectError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You can't change the project of a file")
    default_code = "change_file_project_error"


class ChangeLinkProjectError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You can't change the project of a link")
    default_code = "change_file_attachment_type_error"


# Technical errors


class ProtectedImageError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("You can't delete this picture: It is related to another object")
    default_code = "protected_image_error"

    def __init__(self, relation: Optional[dict] = None):
        detail = (
            _(
                "You can't delete this picture: It is related to an instance of {model} with pk={pk} through field {field}"
            ).format(
                model=relation["model"], pk=relation["pk"], field=relation["field"]
            )
            if relation
            else self.default_detail
        )
        super().__init__(detail=detail)
