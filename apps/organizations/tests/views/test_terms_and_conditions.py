from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateTermsAndConditionsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_create_terms_and_conditions(self):
        self.client.force_authenticate(self.superadmin)
        logo_image = self.get_test_image()
        payload = {
            "name": faker.word(),
            "code": faker.word(),
            "dashboard_title": faker.word(),
            "dashboard_subtitle": faker.word(),
            "website_url": faker.url(),
            "logo_image_id": logo_image.id,
        }
        response = self.client.post(reverse("Organization-list"), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        terms_and_conditions = content.get("terms_and_conditions")
        self.assertIsNotNone(terms_and_conditions)
        self.assertIn("id", terms_and_conditions)
        self.assertEqual(terms_and_conditions["version"], 1)
        self.assertEqual(terms_and_conditions["content"], "")


class UpdateTermsAndConditionsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_terms_and_conditions(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        terms_and_conditions = self.organization.terms_and_conditions
        initial_version = terms_and_conditions.version
        payload = {
            "content": faker.text(),
        }
        response = self.client.patch(
            reverse(
                "TermsAndConditions-detail",
                args=(self.organization.code, terms_and_conditions.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if response.status_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["content"], payload["content"])
            self.assertEqual(content["version"], initial_version + 1)

        # Check that updating with the same content does not increment the version
        if expected_code == status.HTTP_200_OK:
            response = self.client.patch(
                reverse(
                    "TermsAndConditions-detail",
                    args=(self.organization.code, terms_and_conditions.id),
                ),
                payload,
            )
            self.assertEqual(response.status_code, expected_code)
            content = response.json()
            self.assertEqual(content["content"], payload["content"])
            self.assertEqual(content["version"], initial_version + 1)
