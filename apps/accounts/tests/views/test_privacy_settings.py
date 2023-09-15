from django.urls import reverse
from faker import Faker
from rest_framework import status
from parameterized import parameterized

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class RetrieveNotificationSettingsTestCase(JwtAPITestCase):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_200_OK),
        ]
    )
    def test_retrieve_public_notification_settings(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(groups=[organization.get_users()], publication_status=PrivacySettings.PrivacyChoices.PUBLIC)
        user = self.get_test_user(role, organization=organization, owned_instance=instance.privacy_settings)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(instance.keycloak_id,))
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert all(
                response.json()[key] == getattr(instance.privacy_settings, key)
                for key in [
                    "publication_status",
                    "profile_picture",
                    "skills",
                    "socials",
                    "mobile_phone",
                    "personal_email",
                ]
            )
    
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_404_NOT_FOUND),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_404_NOT_FOUND),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_200_OK),
        ]
    )
    def test_retrieve_org_notification_settings(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(groups=[organization.get_users()], publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION)
        user = self.get_test_user(role, organization=organization, owned_instance=instance.privacy_settings)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(instance.keycloak_id,))
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert all(
                response.json()[key] == getattr(instance.privacy_settings, key)
                for key in [
                    "publication_status",
                    "profile_picture",
                    "skills",
                    "socials",
                    "mobile_phone",
                    "personal_email",
                ]
            )
    
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_404_NOT_FOUND),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_404_NOT_FOUND),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_404_NOT_FOUND),
        ]
    )
    def test_retrieve_private_notification_settings(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(groups=[organization.get_users()], publication_status=PrivacySettings.PrivacyChoices.HIDE)
        user = self.get_test_user(role, organization=organization, owned_instance=instance.privacy_settings)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(instance.keycloak_id,))
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert all(
                response.json()[key] == getattr(instance.privacy_settings, key)
                for key in [
                    "publication_status",
                    "profile_picture",
                    "skills",
                    "socials",
                    "mobile_phone",
                    "personal_email",
                ]
            )


class UpdateNotificationSettingsTestCase(JwtAPITestCase):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_notification_settings(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_test_user(role, organization=organization, owned_instance=instance.privacy_settings)
        self.client.force_authenticate(user)
        payload = {
            key: faker.enum(PrivacySettings.PrivacyChoices)
            for key in [
                "publication_status",
                "profile_picture",
                "skills",
                "socials",
                "mobile_phone",
                "personal_email",
            ]
        }
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(instance.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert all(
                response.json()[key] == value
                for key, value in payload.items()
            )
