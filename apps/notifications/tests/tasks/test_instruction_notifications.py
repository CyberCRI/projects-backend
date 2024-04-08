import datetime

from django.core import mail
from django.utils.timezone import make_aware

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from apps.newsfeed.factories import InstructionFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import notify_new_instruction
from apps.organizations.factories import OrganizationFactory


class SendInstructionNotificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # INSTRUCTION 1
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

        leaders_managers = UserFactory.create_batch(2)
        managers = UserFactory.create_batch(2)
        leaders_members = UserFactory.create_batch(2)
        members = UserFactory.create_batch(2)

        cls.people_group.managers.add(*managers, *leaders_managers)
        cls.people_group.members.add(*members, *leaders_members)
        cls.people_group.leaders.add(*leaders_managers, *leaders_members)

        cls.publication_date = make_aware(datetime.datetime.now())

        cls.instruction = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.people_group],
            publication_date=cls.publication_date,
            has_to_be_notified=True,
        )

        # INSTRUCTION 2
        cls.people_group_2 = PeopleGroupFactory(organization=cls.organization)

        leaders_managers_2 = UserFactory.create_batch(2)
        managers_2 = UserFactory.create_batch(2)
        leaders_members_2 = UserFactory.create_batch(2)
        members_2 = UserFactory.create_batch(2)

        cls.people_group_2.managers.add(*managers_2, *leaders_managers_2)
        cls.people_group_2.members.add(*members_2, *leaders_members_2)
        cls.people_group_2.leaders.add(*leaders_managers_2, *leaders_members_2)

        cls.publication_date_2 = make_aware(datetime.datetime.now())
        cls.instruction_2 = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.people_group_2],
            publication_date=cls.publication_date_2,
            has_to_be_notified=False,
        )

        # INSTRUCTION 3
        cls.people_group_3 = PeopleGroupFactory(organization=cls.organization)

        leaders_managers_3 = UserFactory.create_batch(2)
        managers_3 = UserFactory.create_batch(2)
        leaders_members_3 = UserFactory.create_batch(2)
        members_3 = UserFactory.create_batch(2)

        cls.people_group_2.managers.add(*managers_3, *leaders_managers_3)
        cls.people_group_2.members.add(*members_3, *leaders_members_3)
        cls.people_group_2.leaders.add(*leaders_managers_3, *leaders_members_3)

        cls.publication_date_3 = make_aware(
            datetime.datetime.now() + datetime.timedelta(1)
        )
        cls.instruction_3 = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.people_group_3],
            publication_date=cls.publication_date_3,
            has_to_be_notified=True,
        )

    def test_send_instruction_notification(self):
        notify_new_instruction()
        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 8)
        self.assertEqual(len(mail.outbox), 8)
        self.assertEqual(mail.outbox[0].subject, "New instruction")

        group_members = self.people_group.get_all_members()

        for member in group_members:
            notification = notifications.get(receiver=member)
            self.assertEqual(notification.type, Notification.Types.INSTRUCTION)
            self.assertEqual(
                notification.reminder_message_en,
                "You received a new instruction.",
            )
            notify_new_instruction()
            notifications = Notification.objects.all()
            self.assertEqual(notifications.count(), 8)
