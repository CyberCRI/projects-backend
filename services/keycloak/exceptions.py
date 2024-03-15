from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed

# Authentication errors


class KeycloakApiAuthenticationError(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Invalid user credentials")
    default_code = "keycloak_authentication_error"


# Technical errors


class KeycloakAccountNotFound(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Given user does not have a keycloak account")
    default_code = "keycloak_account_not_found"


class RemoteKeycloakAccountNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("No user was found with the given keycloak id")
    default_code = "remote_keycloak_account_not_found"


class MissingRedirectUriError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The 'redirect_uri' parameter is mandatory")
    default_code = "missing_redirect_uri_error"


class InvalidKeycloakEmailTypeError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The given email type is not valid")
    default_code = "invalid_email_type_error"

    def __init__(self, email_type: Optional[str] = None):
        detail = (
            _(f"Email type '{email_type}' is not valid")
            if email_type
            else self.default_detail
        )
        super().__init__(detail=detail)
