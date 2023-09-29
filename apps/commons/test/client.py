from unittest import util

from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.authentication import BearerToken
from apps.accounts.models import ProjectUser

util._MAX_LENGTH = 1000000


class JwtClient(APIClient):
    """Override default `Client` to create a JWT token when `force_login()`.

    This token will then be given in any subsequent request in the
    header `HTTP_AUTHORIZATION`.
    """

    def force_authenticate(  # nosec
        self,
        user: ProjectUser = None,
        token: str = None,
        token_type: str = "JWT",
        through_cookie=False,
    ):
        """Login the given user by creating a JWT token."""
        if user:
            if token is None:
                token = BearerToken.for_user(user)
            if through_cookie:
                self.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME] = token
            else:
                self.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")
        elif token:
            self.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")
