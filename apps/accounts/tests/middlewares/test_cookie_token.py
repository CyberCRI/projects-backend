from django.conf import settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CookieTokenMiddlewareTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(groups=[cls.organization.get_users()])

    def test_authentication_through_cookie(self):
        self.client.force_authenticate(self.user, through_cookie=True)
        payload = {
            "title": faker.sentence(),
            "organizations_codes": [self.organization.code],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        del self.client.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME]
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_authentication_through_cookie_wrong_cookie(self):
        self.client.force_authenticate(self.user, through_cookie=True)
        payload = {
            "title": faker.sentence(),
            "organizations_codes": [self.organization.code],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Modify the cookie to check if the authentication fails as expected
        token = self.client.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME].value
        token = token[1:] + ("a" if token[0] != "a" else "b")
        self.client.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME] = token
        payload = {
            "title": faker.sentence(),
            "organizations_codes": [self.organization.code],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )
