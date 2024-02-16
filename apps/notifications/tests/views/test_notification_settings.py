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
                assert response.status_code == status.HTTP_200_OK
            else:
                assert response.status_code == status.HTTP_404_NOT_FOUND


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
            "followed_project_has_been_edited": faker.boolean(),
            "project_has_been_commented": faker.boolean(),
            "project_has_been_edited": faker.boolean(),
            "project_ready_for_review": faker.boolean(),
            "project_has_been_reviewed": faker.boolean(),
        }
        response = self.client.patch(
            reverse("NotificationSettings-detail", args=(self.user.id,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            notification_settings = self.user.notification_settings
            notification_settings.refresh_from_db()
            assert (
                notification_settings.notify_added_to_project
                == payload["notify_added_to_project"]
            )
            assert (
                notification_settings.announcement_published
                == payload["announcement_published"]
            )
            assert (
                notification_settings.followed_project_has_been_edited
                == payload["followed_project_has_been_edited"]
            )
            assert (
                notification_settings.project_has_been_commented
                == payload["project_has_been_commented"]
            )
            assert (
                notification_settings.project_has_been_edited
                == payload["project_has_been_edited"]
            )
            assert (
                notification_settings.project_ready_for_review
                == payload["project_ready_for_review"]
            )
            assert (
                notification_settings.project_has_been_reviewed
                == payload["project_has_been_reviewed"]
            )
