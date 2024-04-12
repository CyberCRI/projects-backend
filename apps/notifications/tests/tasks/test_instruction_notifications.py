import datetime

from django.core import mail
from django.utils.timezone import make_aware
from faker import Faker

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from apps.newsfeed.factories import InstructionFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_instructions
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class InvitationExpiresNotificationsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    def test_instruction_notification_task(self):
        owner = UserFactory(
            groups=[self.organization.get_admins(), self.people_group.get_leaders()]
        )
        notified = UserFactory(
            groups=[self.organization.get_users(), self.people_group.get_members()]
        )
        not_notified = UserFactory(
            groups=[self.organization.get_users(), self.people_group.get_members()]
        )
        # Disabling notification for 'not_notified'
        not_notified.notification_settings.new_instruction = False
        not_notified.notification_settings.save()

        global_instruction = InstructionFactory(
            organization=self.organization,
            owner=owner,
            has_to_be_notified=True,
            notified=False,
        )
        group_instruction = InstructionFactory(
            organization=self.organization,
            people_groups=[self.people_group],
            owner=owner,
            has_to_be_notified=True,
            notified=False,
        )
        group_planned_instruction = InstructionFactory(
            organization=self.organization,
            people_groups=[self.people_group],
            owner=owner,
            publication_date=make_aware(
                datetime.datetime.now() + datetime.timedelta(7)
            ),
            has_to_be_notified=True,
            notified=False,
        )
        _notify_new_instructions()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 2)
        for user in [notified, not_notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.NEW_INSTRUCTION)
            self.assertEqual(notification.project, None)
            self.assertEqual(notification.organization, self.organization)
            self.assertFalse(notification.to_send)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [notified.email])
        self.assertEqual(mail.outbox[0].subject, "New instruction")

        global_instruction.refresh_from_db()
        group_instruction.refresh_from_db()
        group_planned_instruction.refresh_from_db()
        self.assertTrue(global_instruction.notified)
        self.assertTrue(group_instruction.notified)
        self.assertFalse(group_planned_instruction.notified)

        _notify_new_instructions()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 2)
        self.assertEqual(len(mail.outbox), 1)
