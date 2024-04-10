from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import AccessRequestFactory
from apps.invitations.models import AccessRequest
from apps.notifications.models import Notification
from apps.notifications.tasks import notify_pending_access_requests
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class PendingAccessRequestsNotificationsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.admins = UserFactory.create_batch(3, groups=[cls.organization.get_admins()])

    def test_notification_task(self):
        AccessRequestFactory.create_batch(
            2, organization=self.organization, status=AccessRequest.Status.PENDING
        )
        AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.ACCEPTED
        )
        AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.DECLINED
        )
        notify_pending_access_requests()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 3)
        for admin in self.admins:
            notification = notifications.get(receiver=admin)
            self.assertEqual(
                notification.type, Notification.Types.PENDING_ACCESS_REQUESTS
            )
            self.assertEqual(notification.context["requests_count"], 2)
            self.assertFalse(notification.is_viewed)
            self.assertFalse(notification.to_send)

    def test_merged_notifications_task(self):
        AccessRequestFactory.create_batch(
            2, organization=self.organization, status=AccessRequest.Status.PENDING
        )
        AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.ACCEPTED
        )
        AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.DECLINED
        )
        notify_pending_access_requests()
        AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.PENDING
        )
        notify_pending_access_requests()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 3)
        for admin in self.admins:
            notification = notifications.get(receiver=admin)
            self.assertEqual(
                notification.type, Notification.Types.PENDING_ACCESS_REQUESTS
            )
            self.assertEqual(notification.context["requests_count"], 3)
            self.assertFalse(notification.is_viewed)
            self.assertFalse(notification.to_send)
