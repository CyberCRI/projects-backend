from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class KeycloakAccountNotFound(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Given user does not have a keycloak account")
    default_code = "keycloak_account_not_found"


class RemoteKeycloakAccountNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("No user was found with the given keycloak id")
    default_code = "remote_keycloak_account_not_found"
