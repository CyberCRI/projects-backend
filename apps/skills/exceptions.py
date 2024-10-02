from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

# Technical errors


class UserIDIsNotProvidedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("User ID must be provided through url")
    default_code = "user_id_is_not_provided"


class UserCannotMentorError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This user cannot be a mentor for this skill")
    default_code = "user_cannot_mentor"


class UserDoesNotNeedMentorError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This user does not need a mentor for this skill")
    default_code = "user_does_not_need_mentor"


class SkillAlreadyAddedError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("You already have this skill in your profile")
    default_code = "skill_already_added"


# Validation errors


class UpdateWrongTypeTagError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Only custom tags can be updated")
    default_code = "update_wrong_type_tag"


class UpdateWrongTypeTagClassificationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Only custom tags classifications can be updated")
    default_code = "update_wrong_type_tag_classification"
