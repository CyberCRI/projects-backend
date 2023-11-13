from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class GoogleGroupEmailUnavailable(APIException):
    status_code = 409
    default_detail = _("This email is already used by another group")
    default_code = "google_error"


class GoogleUserEmailUnavailable(APIException):
    status_code = 409
    default_detail = _("This email is already used by another user")
    default_code = "google_error"


class GoogleUserNotSynced(Exception):
    def __init__(self, projects_email: str, google_email: str):
        super().__init__(f"User not synced : {projects_email} != {google_email}")
