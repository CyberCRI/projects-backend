from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory


class NotificationsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])

    def test_list(self):
        notification = NotificationFactory(
            project=self.project, organization=self.organization
        )
        self.client.force_authenticate(notification.receiver)
        response = self.client.get(
            reverse("Notification-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_status_change(self):
        user = UserFactory()
        notifications = NotificationFactory.create_batch(
            5, receiver=user, project=self.project, is_viewed=False
        )
        unchanged = NotificationFactory(
            project=self.project, is_viewed=False, organization=self.organization
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Notification-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for notification in notifications:
            notification.refresh_from_db()
            self.assertTrue(notification.is_viewed)
        unchanged.refresh_from_db()
        self.assertFalse(unchanged.is_viewed)
