from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

# Technical errors


class UserCannotMentorError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This user cannot be a mentor for this skill")
    default_code = "user_cannot_mentor"


class UserDoesNotNeedMentorError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("This user does not need a mentor for this skill")
    default_code = "user_does_not_need_mentor"
