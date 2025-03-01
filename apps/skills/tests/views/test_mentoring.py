"""
Test cases for the mentoring views

To test the content of the emails, you can run this command in a backend shell:

DO NOT RUN IN PRODUCTION!

```shell
python manage.py test_mentoring_emails
```
"""

from django.core import mail
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import (
    MentorCreatedMentoringFactory,
    MentoreeCreatedMentoringFactory,
    SkillFactory,
    TagFactory,
)
from apps.skills.models import Mentoring, MentoringMessage
from apps.skills.views import MentoringViewSet

faker = Faker()


class ViewMentoringTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.mentoring = MentorCreatedMentoringFactory(organization=cls.organization)
        MentoreeCreatedMentoringFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND),
            (
                "mentor",
                status.HTTP_200_OK,
            ),
            (
                "mentoree",
                status.HTTP_200_OK,
            ),
        ]
    )
    def test_retrieve_mentoring(self, role, expected_code):
        if role == "mentor":
            user = self.mentoring.mentor
        elif role == "mentoree":
            user = self.mentoring.mentoree
        else:
            user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "Mentoring-detail", args=(self.organization.code, self.mentoring.id)
            )
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["id"], self.mentoring.id)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED, False),
            (TestRoles.DEFAULT, status.HTTP_200_OK, False),
            ("mentor", status.HTTP_200_OK, True),
            ("mentoree", status.HTTP_200_OK, True),
        ]
    )
    def test_list_mentoring(self, role, expected_code, retrieved):
        if role == "mentor":
            user = self.mentoring.mentor
        elif role == "mentoree":
            user = self.mentoring.mentoree
        else:
            user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "Mentoring-list",
                args=(self.organization.code,),
            )
        )
        self.assertEqual(response.status_code, expected_code)
        if retrieved:
            content = response.json()["results"]
            self.assertEqual(len(content), 1)
            self.assertSetEqual(
                {mentoring["id"] for mentoring in content},
                {self.mentoring.id},
            )


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
                args=(
                    self.organization.code,
                    self.mentor_skill.id,
                ),
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
            self.assertEqual(mentoring.organization, self.organization)
            self.assertEqual(mentoring.mentor, self.mentor)
            self.assertEqual(mentoring.mentoree, user)
            self.assertEqual(mentoring.skill, self.mentor_skill)
            self.assertEqual(mentoring.created_by, user)
            self.assertIsNone(mentoring.status)
            self.assertTrue(
                MentoringMessage.objects.filter(
                    mentoring=mentoring, content=payload["content"], sender=user
                ).exists()
            )

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
                args=(
                    self.organization.code,
                    self.mentoree_skill.id,
                ),
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
            self.assertEqual(mentoring.organization, self.organization)
            self.assertEqual(mentoring.mentor, user)
            self.assertEqual(mentoring.mentoree, self.mentoree)
            self.assertEqual(mentoring.skill, self.mentoree_skill)
            self.assertEqual(mentoring.created_by, user)
            self.assertIsNone(mentoring.status)
            self.assertTrue(
                MentoringMessage.objects.filter(
                    mentoring=mentoring, content=payload["content"], sender=user
                ).exists()
            )


class RespondToMentoringTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.mentor_created = MentorCreatedMentoringFactory(
            organization=cls.organization
        )
        cls.mentoree_created = MentoreeCreatedMentoringFactory(
            organization=cls.organization
        )

    @parameterized.expand(
        [
            (
                TestRoles.ANONYMOUS,
                Mentoring.MentoringStatus.ACCEPTED.value,
                status.HTTP_401_UNAUTHORIZED,
            ),
            (
                TestRoles.DEFAULT,
                Mentoring.MentoringStatus.ACCEPTED.value,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                "mentor",
                Mentoring.MentoringStatus.ACCEPTED.value,
                status.HTTP_403_FORBIDDEN,
            ),
            ("mentoree", Mentoring.MentoringStatus.ACCEPTED.value, status.HTTP_200_OK),
            ("mentoree", Mentoring.MentoringStatus.REJECTED.value, status.HTTP_200_OK),
            ("mentoree", Mentoring.MentoringStatus.PENDING.value, status.HTTP_200_OK),
        ]
    )
    def test_respond_to_mentor_request(self, role, mentoring_status, expected_code):
        if role == "mentor":
            user = self.mentor_created.mentor
        elif role == "mentoree":
            user = self.mentor_created.mentoree
        else:
            user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        payload = {
            "status": mentoring_status,
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-respond",
                args=(
                    self.organization.code,
                    self.mentor_created.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentor_created.mentor.email])
            self.assertIn(payload["content"], email.body)

            content = response.json()
            self.assertEqual(content["status"], mentoring_status)
            self.assertTrue(
                MentoringMessage.objects.filter(
                    mentoring=self.mentor_created,
                    content=payload["content"],
                    sender=user,
                ).exists()
            )
        if expected_code == status.HTTP_403_FORBIDDEN:
            self.assertApiPermissionError(
                response,
                "You cannot change the status of a mentoring request you created",
            )

    @parameterized.expand(
        [
            (
                TestRoles.ANONYMOUS,
                Mentoring.MentoringStatus.ACCEPTED.value,
                status.HTTP_401_UNAUTHORIZED,
            ),
            (
                TestRoles.DEFAULT,
                Mentoring.MentoringStatus.ACCEPTED.value,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                "mentoree",
                Mentoring.MentoringStatus.ACCEPTED.value,
                status.HTTP_403_FORBIDDEN,
            ),
            ("mentor", Mentoring.MentoringStatus.ACCEPTED.value, status.HTTP_200_OK),
            ("mentor", Mentoring.MentoringStatus.REJECTED.value, status.HTTP_200_OK),
            ("mentor", Mentoring.MentoringStatus.PENDING.value, status.HTTP_200_OK),
        ]
    )
    def test_respond_to_mentoree_request(self, role, mentoring_status, expected_code):
        if role == "mentor":
            user = self.mentoree_created.mentor
        elif role == "mentoree":
            user = self.mentoree_created.mentoree
        else:
            user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        payload = {
            "status": mentoring_status,
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-respond",
                args=(
                    self.organization.code,
                    self.mentoree_created.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.mentoree_created.mentoree.email])
            self.assertIn(payload["content"], email.body)
            content = response.json()
            self.assertEqual(content["status"], mentoring_status)
            self.assertTrue(
                MentoringMessage.objects.filter(
                    mentoring=self.mentoree_created,
                    content=payload["content"],
                    sender=user,
                ).exists()
            )
        if expected_code == status.HTTP_403_FORBIDDEN:
            self.assertApiPermissionError(
                response,
                "You cannot change the status of a mentoring request you created",
            )


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
                args=(
                    self.organization.code,
                    self.mentor_wrong_skill.id,
                ),
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
                args=(
                    self.organization.code,
                    self.mentoree_wrong_skill.id,
                ),
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
                args=(
                    self.organization.code,
                    self.mentoree_skill.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentoree",
                args=(
                    self.organization.code,
                    self.mentoree_skill.id,
                ),
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
                args=(
                    self.organization.code,
                    self.mentor_skill.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post(
            reverse(
                "Mentoring-contact-mentor",
                args=(
                    self.organization.code,
                    self.mentor_skill.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response, "You already made a mentoring request for this skill"
        )

    def test_update_mentoring_status_with_invalid_status(self):
        mentoring = MentoreeCreatedMentoringFactory(organization=self.organization)
        self.client.force_authenticate(mentoring.mentor)
        payload = {
            "status": faker.word(),
            "content": faker.text(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-respond",
                args=(
                    self.organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"status": [f"\"{payload['status']}\" is not a valid choice."]},
        )


class MiscMentoringTestCase(JwtAPITestCase):
    def test_get_skill_name(self):
        user = UserFactory()

        tag = TagFactory(title_fr="")
        skill = SkillFactory(user=user, tag=tag)
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "en"),
            tag.title_en,
        )
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "fr"),
            tag.title_en,
        )

        tag = TagFactory(title_en="")
        skill = SkillFactory(user=user, tag=tag)
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "en"),
            tag.title_fr,
        )
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "fr"),
            tag.title_fr,
        )

        tag = TagFactory()
        skill = SkillFactory(user=user, tag=tag)
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "en"),
            tag.title_en,
        )
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "fr"),
            tag.title_fr,
        )

        tag = TagFactory(title_en="", title_fr=None)
        skill = SkillFactory(user=user, tag=tag)
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "en"),
            tag.title,
        )
        self.assertEqual(
            MentoringViewSet.get_skill_name(skill, "fr"),
            tag.title,
        )
