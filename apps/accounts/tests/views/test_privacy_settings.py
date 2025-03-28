from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class RetrievePrivacySettingsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
        )
        cls.private_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
        )
        cls.org_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_200_OK),
            (TestRoles.DEFAULT, status.HTTP_200_OK),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_200_OK),
        ]
    )
    def test_retrieve_public_privacy_settings(self, role, expected_code):
        organization = self.organization
        instance = self.public_user
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance.privacy_settings
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(instance.id,))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            for key in [
                "publication_status",
                "profile_picture",
                "skills",
                "socials",
                "mobile_phone",
                "email",
            ]:
                self.assertEqual(content[key], getattr(instance.privacy_settings, key))

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_404_NOT_FOUND),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_200_OK),
        ]
    )
    def test_retrieve_org_privacy_settings(self, role, expected_code):
        organization = self.organization
        instance = self.org_user
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance.privacy_settings
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(instance.id,))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            for key in [
                "publication_status",
                "profile_picture",
                "skills",
                "socials",
                "mobile_phone",
                "email",
            ]:
                self.assertEqual(content[key], getattr(instance.privacy_settings, key))

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_404_NOT_FOUND),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_404_NOT_FOUND),
        ]
    )
    def test_retrieve_private_privacy_settings(self, role, expected_code):
        organization = self.organization
        instance = self.private_user
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance.privacy_settings
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(instance.id,))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            for key in [
                "publication_status",
                "profile_picture",
                "skills",
                "socials",
                "mobile_phone",
                "email",
            ]:
                self.assertEqual(content[key], getattr(instance.privacy_settings, key))


class UpdatePrivacySettingsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.instance = UserFactory(groups=[cls.organization.get_users()])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_privacy_settings(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role,
            instances=[self.organization],
            owned_instance=self.instance.privacy_settings,
        )
        self.client.force_authenticate(user)
        payload = {
            key: faker.enum(PrivacySettings.PrivacyChoices)
            for key in [
                "publication_status",
                "profile_picture",
                "skills",
                "socials",
                "mobile_phone",
                "email",
            ]
        }
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(self.instance.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            for key, value in payload.items():
                self.assertEqual(content[key], value)
