from datetime import timedelta

from django.core import mail
from django.utils import timezone
from faker import Faker
from parameterized import parameterized

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import (
    MentorCreatedMentoringFactory,
    MentoreeCreatedMentoringFactory,
)
from apps.skills.models import Mentoring, MentoringMessage
from apps.skills.tasks import _send_mentoring_reminder

faker = Faker()


class MentoringReminderTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.mentor = UserFactory()
        cls.mentoree = UserFactory()

    @parameterized.expand(
        [
            (None, 3, True),
            (None, 10, True),
            (Mentoring.MentoringStatus.PENDING, 3, True),
            (Mentoring.MentoringStatus.PENDING, 10, True),
            (Mentoring.MentoringStatus.ACCEPTED, 3, False),
            (Mentoring.MentoringStatus.REJECTED, 3, False),
            (Mentoring.MentoringStatus.ACCEPTED, 10, False),
            (Mentoring.MentoringStatus.REJECTED, 10, False),
        ]
    )
    def test_mentoree_reminder(self, mentoring_status, inactivity_days, email_sent):
        # Mentor created mentoring with latest message at the given date
        mentoring_1 = MentorCreatedMentoringFactory(
            organization=self.organization,
            mentor=self.mentor,
            mentoree=self.mentoree,
            status=mentoring_status,
        )
        message_1 = MentoringMessage.objects.create(
            mentoring=mentoring_1,
            sender=self.mentor,
            content=faker.text(),
        )

        # Mentor created mentoring with message at the given date and a more recent one
        mentoring_2 = MentorCreatedMentoringFactory(
            organization=self.organization,
            mentor=self.mentor,
            mentoree=self.mentoree,
            status=mentoring_status,
        )
        message_2 = MentoringMessage.objects.create(
            mentoring=mentoring_2,
            sender=self.mentor,
            content=faker.text(),
        )
        MentoringMessage.objects.create(
            mentoring=mentoring_2,
            sender=self.mentoree,
            content=faker.text(),
        )

        MentoringMessage.objects.filter(id__in=[message_1.id, message_2.id]).update(
            created_at=timezone.now() - timedelta(days=inactivity_days)
        )

        _send_mentoring_reminder(inactivity_days)
        if email_sent:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentoree.email])
            skill_name = getattr(
                mentoring_1.skill.tag, f"title_{self.mentoree.language}"
            )
            if inactivity_days == 3:
                subject = f"Do you want to be mentored in {skill_name}? (reminder)"
            else:
                subject = f"Do you want to be mentored in {skill_name}? (last reminder)"
            self.assertEqual(email.subject, subject)
        else:
            self.assertEqual(len(mail.outbox), 0)

    @parameterized.expand(
        [
            (None, 3, True),
            (None, 10, True),
            (Mentoring.MentoringStatus.PENDING, 3, True),
            (Mentoring.MentoringStatus.PENDING, 10, True),
            (Mentoring.MentoringStatus.ACCEPTED, 3, False),
            (Mentoring.MentoringStatus.REJECTED, 3, False),
            (Mentoring.MentoringStatus.ACCEPTED, 10, False),
            (Mentoring.MentoringStatus.REJECTED, 10, False),
        ]
    )
    def test_mentor_reminder(self, mentoring_status, inactivity_days, email_sent):
        # Mentor created mentoring with latest message at the given date
        mentoring_1 = MentoreeCreatedMentoringFactory(
            organization=self.organization,
            mentor=self.mentor,
            mentoree=self.mentoree,
            status=mentoring_status,
        )
        message_1 = MentoringMessage.objects.create(
            mentoring=mentoring_1,
            sender=self.mentoree,
            content=faker.text(),
        )

        # Mentor created mentoring with message at the given date and a more recent one
        mentoring_2 = MentoreeCreatedMentoringFactory(
            organization=self.organization,
            mentor=self.mentor,
            mentoree=self.mentoree,
            status=mentoring_status,
        )
        message_2 = MentoringMessage.objects.create(
            mentoring=mentoring_2,
            sender=self.mentoree,
            content=faker.text(),
        )
        MentoringMessage.objects.create(
            mentoring=mentoring_2,
            sender=self.mentor,
            content=faker.text(),
        )

        MentoringMessage.objects.filter(id__in=[message_1.id, message_2.id]).update(
            created_at=timezone.now() - timedelta(days=inactivity_days)
        )

        _send_mentoring_reminder(inactivity_days)
        if email_sent:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentor.email])
            if inactivity_days == 3:
                subject = f"Can you mentor {self.mentoree.given_name.capitalize()}? (reminder)"
            else:
                subject = f"Can you mentor {self.mentoree.given_name.capitalize()}? (last reminder)"
            self.assertEqual(email.subject, subject)
        else:
            self.assertEqual(len(mail.outbox), 0)
