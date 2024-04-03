from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import AccessRequestFactory
from apps.invitations.models import AccessRequest
from apps.notifications.tasks import notify_pending_access_requests
from apps.notifications.models import Notification
from apps.organizations.factories import OrganizationFactory


class SendAccessRequestNotificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.admins = UserFactory.create_batch(3, groups=[cls.organization.get_admins()])
        cls.user_1 = UserFactory(groups=[cls.organization.get_users()])
        cls.access_requests_a = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.ACCEPTED
        )
        cls.access_requests_b = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.DECLINED
        )
        cls.access_requests_c = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.PENDING
        )
        cls.access_requests_d = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.PENDING
        )

    def test_send_access_request_notification(self):
        notify_pending_access_requests()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 3)
        for admin in self.admins:
            notification = notifications.get(receiver=admin)
            self.assertEqual(notification.type, Notification.Types.PENDING_ACCESS_REQUESTS)
            self.assertEqual(notification.context["requests_count"], 2)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(
                notification.reminder_message_en,
                "Respond to 2 pending access requests!",
            )
            self.assertEqual(
                notification.reminder_message_fr,
                "Répondez à 2 demandes d'accès en attente!",
            )
