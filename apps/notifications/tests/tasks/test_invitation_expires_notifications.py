import datetime

from django.core import mail
from django.utils.timezone import make_aware
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import InvitationFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import send_invitations_reminder
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class InvitationExpiresNotificationsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.admins = UserFactory.create_batch(3, groups=[cls.organization.get_admins()])
        cls.owner = cls.admins[0]

    def test_invitation_expires_in_one_week_task(self):
        InvitationFactory(
            organization=self.organization,
            owner=self.owner,
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(7)),
        )
        InvitationFactory(
            organization=self.organization,
            owner=self.owner,
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(14)),
        )
        send_invitations_reminder()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 3)
        for admin in self.admins:
            notification = notifications.get(receiver=admin)
            self.assertEqual(
                notification.type, Notification.Types.INVITATION_WEEK_REMINDER
            )
            self.assertFalse(notification.is_viewed)
        self.assertEqual(len(mail.outbox), 3)
        for message in mail.outbox:
            self.assertEqual(message.subject, "Registration link to expire in one week")

    def test_invitation_expires_in_one_day_task(self):
        InvitationFactory(
            organization=self.organization,
            owner=self.owner,
            expire_at=make_aware(datetime.datetime.now()),
        )
        InvitationFactory(
            organization=self.organization,
            owner=self.owner,
            expire_at=make_aware(datetime.datetime.now()) + datetime.timedelta(1),
        )
        InvitationFactory(
            organization=self.organization,
            owner=self.owner,
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(2)),
        )
        send_invitations_reminder()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 3)
        for admin in self.admins:
            notification = notifications.get(receiver=admin)
            self.assertEqual(
                notification.type, Notification.Types.INVITATION_TODAY_REMINDER
            )
            self.assertFalse(notification.is_viewed)
        self.assertEqual(len(mail.outbox), 3)
        for message in mail.outbox:
            self.assertEqual(message.subject, "Registration link to expire today")
