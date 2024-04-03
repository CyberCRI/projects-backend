import datetime

from django.core import mail
from django.utils.timezone import make_aware

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import InvitationFactory
from apps.invitations.models import Invitation
from apps.notifications.tasks import send_invitations_reminder
from apps.organizations.factories import OrganizationFactory


class SendInvitationReminderTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.admins = UserFactory.create_batch(3, groups=[cls.organization.get_admins()])
        cls.owner = cls.admins[0]

    def test_send_invitations_one_week_reminder_task(self):
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
        invitations = Invitation.objects.all()
        self.assertEqual(invitations.count(), 2)
        self.assertEqual(len(mail.outbox), 3)
        for message in mail.outbox:
            self.assertEqual(
                message.subject, "Registration link to expire in one week"
            )

    def test_send_invitations_last_day_reminder_task(self):
        InvitationFactory(
            organization=self.organization,
            owner=self.owner,
            expire_at=make_aware(datetime.datetime.now())
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
        invitations = Invitation.objects.all()
        self.assertEqual(invitations.count(), 3)
        self.assertEqual(len(mail.outbox), 3)
        for message in mail.outbox:
            self.assertEqual(
                message.subject, "Registration link to expire today"
            )
