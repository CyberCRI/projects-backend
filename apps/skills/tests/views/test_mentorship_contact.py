from django.core import mail
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import SkillFactory

faker = Faker()


class MentorshipContactTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.mentor = UserFactory(groups=[cls.organization.get_users()])
        cls.mentoree = UserFactory(groups=[cls.organization.get_users()])
        cls.mentor_skill = SkillFactory(user=cls.mentor, can_mentor=True)
        cls.mentoree_skill = SkillFactory(user=cls.mentoree, needs_mentor=True)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_contact_mentor(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "MentorshipContact-contact-mentor",
                args=(organization.code, self.mentor_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentor.email])
            self.assertIn(payload["title"], email.body)
            self.assertIn(payload["content"], email.body)
            self.assertIn(payload["reply_to"], email.body)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_contact_mentoree(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "MentorshipContact-contact-mentoree",
                args=(organization.code, self.mentoree_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentoree.email])
            self.assertIn(payload["title"], email.body)
            self.assertIn(payload["content"], email.body)
            self.assertIn(payload["reply_to"], email.body)


class ValidateMentorshipContactTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.mentor = UserFactory(groups=[cls.organization.get_users()])
        cls.mentoree = UserFactory(groups=[cls.organization.get_users()])
        cls.mentor_skill = SkillFactory(user=cls.mentor, can_mentor=True)
        cls.mentoree_skill = SkillFactory(user=cls.mentoree, needs_mentor=True)
        cls.mentor_wrong_skill = SkillFactory(user=cls.mentor)
        cls.mentoree_wrong_skill = SkillFactory(user=cls.mentoree)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_contact_mentor_for_wrong_skill(self):
        organization = self.organization
        user = self.superadmin
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "MentorshipContact-contact-mentor",
                args=(organization.code, self.mentor_wrong_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "This user cannot be a mentor for this skill"
        )

    def test_contact_mentoree_for_wrong_skill(self):
        organization = self.organization
        user = self.superadmin
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "MentorshipContact-contact-mentoree",
                args=(organization.code, self.mentoree_wrong_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "This user does not need a mentor for this skill"
        )
