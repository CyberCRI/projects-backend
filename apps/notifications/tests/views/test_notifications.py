from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.notifications.factories import NotificationFactory


class NotificationsTestCase(JwtAPITestCase):
    def test_list(self):
        notification = NotificationFactory()
        self.client.force_authenticate(notification.receiver)
        response = self.client.get(reverse("Notification-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_status_change(self):
        user = UserFactory()
        notifications = NotificationFactory.create_batch(
            5, receiver=user, is_viewed=False
        )
        unchanged = NotificationFactory(is_viewed=False)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Notification-list"))
        assert response.status_code == status.HTTP_200_OK
        for notification in notifications:
            notification.refresh_from_db()
            assert notification.is_viewed is True
        unchanged.refresh_from_db()
        assert unchanged.is_viewed is False
