from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class EmailTypeMissingError(APIException):
    status_code = 400
    default_detail = _(
        "email_type query parameter is missing. Choices are : admin_created, invitation, reset_password"
    )
    default_code = "keycloak_email_type_missing"
