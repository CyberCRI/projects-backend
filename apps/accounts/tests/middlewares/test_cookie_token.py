from django.conf import settings
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase


class CookieTokenMiddlewareTestCase(JwtAPITestCase):
    def test_authentication_through_cookie(self):
        self.client.force_authenticate(UserFactory(), through_cookie=True)

        response = self.client.post(reverse("Project-list"), data={})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )

        del self.client.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME]
        response = self.client.post(reverse("Project-list"), data={})
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_authentication_through_cookie_wrong_cookie(self):
        self.client.force_authenticate(UserFactory(), through_cookie=True)

        response = self.client.post(reverse("Project-list"), data={})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )

        # Modify the cookie to check if the authentication fails as expected
        token = self.client.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME].value
        token = token[1:] + ("a" if token[0] != "a" else "b")
        self.client.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME] = token
        response = self.client.post(reverse("Project-list"), data={})
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )
