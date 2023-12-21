from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class KeycloakAccountNotFound(APIException):
    status_code = 400
    default_detail = _("Given user does not have a keycloak account.")
    default_code = "keycloak_error"
