import datetime

from django.core import mail
from django.utils.timezone import make_aware

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import InvitationFactory
from apps.invitations.models import Invitation
from apps.invitations.tasks import send_invitations_reminder


class SendInvitationReminderTestCase(JwtAPITestCase):
    def test_send_invitations_one_week_reminder_task(self):
        owner = UserFactory()
        InvitationFactory(
            owner=owner,
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(7)),
        )
        InvitationFactory(
            owner=owner,
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(14)),
        )

        send_invitations_reminder()
        invitations = Invitation.objects.all()
        self.assertEqual(invitations.count(), 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject, "Registration link to expire in one week"
        )

    def test_send_invitations_last_day_reminder_task(self):
        owner = UserFactory()
        InvitationFactory(owner=owner, expire_at=make_aware(datetime.datetime.now()))
        InvitationFactory(
            owner=owner,
            expire_at=make_aware(datetime.datetime.now()) + datetime.timedelta(1),
        )
        InvitationFactory(
            owner=owner,
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(2)),
        )
        send_invitations_reminder()
        invitations = Invitation.objects.all()
        self.assertEqual(invitations.count(), 3)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Registration link to expire today")
