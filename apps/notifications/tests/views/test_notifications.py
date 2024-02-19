from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.notifications.factories import NotificationFactory
from apps.projects.factories import ProjectFactory


class NotificationsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = ProjectFactory()

    def test_list(self):
        notification = NotificationFactory(project=self.project)
        self.client.force_authenticate(notification.receiver)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_status_change(self):
        user = UserFactory()
        notifications = NotificationFactory.create_batch(
            5, receiver=user, project=self.project, is_viewed=False
        )
        unchanged = NotificationFactory(project=self.project, is_viewed=False)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for notification in notifications:
            notification.refresh_from_db()
            assert notification.is_viewed is True
        unchanged.refresh_from_db()
        assert unchanged.is_viewed is False
