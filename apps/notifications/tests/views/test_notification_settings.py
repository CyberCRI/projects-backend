from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class RetrieveNotificationSettingsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
        )
        cls.org_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
            groups=[cls.organization.get_users()],
        )
        cls.private_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
            groups=[cls.organization.get_users()],
        )
        cls.users = {
            "public": cls.public_user,
            "org": cls.org_user,
            "private": cls.private_user,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.ORG_VIEWER, ("public", "org")),
        ]
    )
    def test_retrieve_notification_settings(
        self, role, retrieved_notification_settings
    ):
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.private_user
        )
        self.client.force_authenticate(user)
        for publication_status, user in self.users.items():
            response = self.client.get(
                reverse("NotificationSettings-detail", args=(user.id,))
            )
            if publication_status in retrieved_notification_settings:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UpdateNotificationSettingsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_notification_settings(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.user
        )
        self.client.force_authenticate(user)
        payload = {
            "notify_added_to_project": faker.boolean(),
            "announcement_published": faker.boolean(),
            "announcement_has_new_application": faker.boolean(),
            "followed_project_has_been_edited": faker.boolean(),
            "project_has_been_commented": faker.boolean(),
            "project_has_been_edited": faker.boolean(),
            "project_ready_for_review": faker.boolean(),
            "project_has_been_reviewed": faker.boolean(),
            "project_has_new_private_message": faker.boolean(),
            "category_project_created": faker.boolean(),
            "category_project_updated": faker.boolean(),
            "comment_received_a_response": faker.boolean(),
            "organization_has_new_access_request": faker.boolean(),
            "invitation_link_will_expire": faker.boolean(),
            "new_instruction": faker.boolean(),
        }
        response = self.client.patch(
            reverse("NotificationSettings-detail", args=(self.user.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            notification_settings = self.user.notification_settings
            notification_settings.refresh_from_db()
            for field, value in payload.items():
                self.assertEqual(getattr(notification_settings, field), value)
