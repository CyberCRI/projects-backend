from typing import Callable, Optional, Tuple

from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response


class CookieTokenMiddleware:
    """Allow authentication through a cookie `JWT_ACCESS_TOKEN_COOKIE_NAME`."""

    get_response: Callable[[Request], Response]

    def __init__(self, get_response: Callable[[Request], Response]):
        self.get_response = get_response

    def _get_token(self, request: Request) -> Tuple[Optional[str], str]:
        """Try to retrieve the JWT access token from the headers or cookies."""
        if "HTTP_AUTHORIZATION" in request.META:
            token = request.META["HTTP_AUTHORIZATION"].split(" ", 1)
            return token[1], token[0]
        return request.COOKIES.get(settings.JWT_ACCESS_TOKEN_COOKIE_NAME, None), "JWT"

    def __call__(self, request: Request) -> Response:
        """Retrieve the token from either the headers or cookies."""
        token, token_type = self._get_token(request)

        # Ensure token (if any) is set in the header to proceed with the authentication
        if token is not None:
            request.META["HTTP_AUTHORIZATION"] = f"{token_type} {token}"

        return self.get_response(request)
