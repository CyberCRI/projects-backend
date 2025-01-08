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
from apps.skills.models import Mentoring

faker = Faker()


class CreateMentoringTestCase(JwtAPITestCase):
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
            (TestRoles.DEFAULT, status.HTTP_200_OK),
        ]
    )
    def test_contact_mentor(self, role, expected_code):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        payload = {
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentor",
                args=(self.organization.code, self.mentor_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentor.email])
            self.assertIn(payload["content"], email.body)

            content = response.json()
            mentoring = Mentoring.objects.filter(id=content["id"])
            self.assertTrue(mentoring.exists())
            mentoring = mentoring.get()
            self.assertEqual(mentoring.mentor, self.mentor)
            self.assertEqual(mentoring.mentoree, user)
            self.assertEqual(mentoring.skill, self.mentor_skill)
            self.assertEqual(mentoring.status, Mentoring.MentoringStatus.PENDING.value)
            self.assertEqual(mentoring.created_by, user)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_200_OK),
        ]
    )
    def test_contact_mentoree(self, role, expected_code):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        payload = {
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentoree",
                args=(self.organization.code, self.mentoree_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentoree.email])
            self.assertIn(payload["content"], email.body)

            content = response.json()
            mentoring = Mentoring.objects.filter(id=content["id"])
            self.assertTrue(mentoring.exists())
            mentoring = mentoring.get()
            self.assertEqual(mentoring.mentor, user)
            self.assertEqual(mentoring.mentoree, self.mentoree)
            self.assertEqual(mentoring.skill, self.mentoree_skill)
            self.assertEqual(mentoring.status, Mentoring.MentoringStatus.PENDING.value)
            self.assertEqual(mentoring.created_by, user)


class ValidateMentoringTestCase(JwtAPITestCase):
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
        self.client.force_authenticate(self.superadmin)
        payload = {
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentor",
                args=(self.organization.code, self.mentor_wrong_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "This user cannot be a mentor for this skill"
        )

    def test_contact_mentoree_for_wrong_skill(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentoree",
                args=(self.organization.code, self.mentoree_wrong_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "This user does not need a mentor for this skill"
        )

    def test_duplicate_mentoree_request(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentoree",
                args=(self.organization.code, self.mentoree_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentoree",
                args=(self.organization.code, self.mentoree_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "You already made a mentoring request for this skill"
        )

    def test_duplicate_mentor_request(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentor",
                args=(self.organization.code, self.mentor_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentor",
                args=(self.organization.code, self.mentor_skill.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "You already made a mentoring request for this skill"
        )
