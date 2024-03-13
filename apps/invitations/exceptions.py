from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

# Technical errors


class InvalidEmailTypeError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The email type is not valid")
    default_code = "invalid_email_type_error"

    def __init__(self, email_type: Optional[str] = None):
        detail = (
            _(f"The email type '{email_type}' is not valid")
            if email_type
            else self.default_detail
        )
        super().__init__(detail=detail)


# Validation errors


class PeopleGroupOrganizationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("People group must belong to the invitation's organization")
    default_code = "people_group_organization_error"


class InvitationOrganizationChangeError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot change the organization of an invitation")
    default_code = "invitation_organization_change_error"


class InvitationUserAlreadyMemberError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This user is already a member of this organization")
    default_code = "invitation_user_already_member_error"


class InvitationUserAlreadyExistsError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A user with this email already exists")
    default_code = "invitation_user_already_exists_error"


class InvitationOrganizationAccessRequestDisabledError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This organization does not accept access requests")
    default_code = "invitation_organization_access_request_disabled_error"
