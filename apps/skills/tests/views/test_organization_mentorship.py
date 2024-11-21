from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import SkillFactory, TagFactory

faker = Faker()


class OrganizationMentorshipTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

        cls.public_public_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
        )
        cls.public_public_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.PUBLIC
        )
        cls.public_public_user.privacy_settings.save()

        # Add another user with the same privacy settings, but with only one skill
        # This is to test that the privacy settings are retrieved in the correct order
        cls.public_public_user_2 = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
        )
        cls.public_public_user_2.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.PUBLIC
        )
        cls.public_public_user_2.privacy_settings.save()

        cls.private_public_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
        )
        cls.private_public_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.PUBLIC
        )
        cls.private_public_user.privacy_settings.save()

        cls.org_public_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
        )
        cls.org_public_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.PUBLIC
        )
        cls.org_public_user.privacy_settings.save()

        cls.public_private_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
        )
        cls.public_private_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.HIDE
        )
        cls.public_private_user.privacy_settings.save()

        cls.private_private_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
        )
        cls.private_private_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.HIDE
        )
        cls.private_private_user.privacy_settings.save()

        cls.org_private_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
        )
        cls.org_private_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.HIDE
        )
        cls.org_private_user.privacy_settings.save()

        cls.public_org_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
        )
        cls.public_org_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.ORGANIZATION
        )
        cls.public_org_user.privacy_settings.save()

        cls.private_org_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
        )
        cls.private_org_user.privacy_settings.skills = (
            PrivacySettings.PrivacyChoices.ORGANIZATION
        )
        cls.private_org_user.privacy_settings.save()

        cls.other_user = UserFactory(
            groups=[cls.organization.get_users()],
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
        )
        cls.other_user.privacy_settings.skills = PrivacySettings.PrivacyChoices.PUBLIC
        cls.other_user.privacy_settings.save()

        cls.users = {
            "public_public": cls.public_public_user,
            "public_public_2": cls.public_public_user_2,
            "private_public": cls.private_public_user,
            "org_public": cls.org_public_user,
            "public_private": cls.public_private_user,
            "private_private": cls.private_private_user,
            "org_private": cls.org_private_user,
            "public_org": cls.public_org_user,
            "private_org": cls.private_org_user,
            "other": cls.other_user,
        }

        cls.mentor_skill_1 = TagFactory()
        cls.mentor_skill_2 = TagFactory()

        cls.mentoree_skill_1 = TagFactory()
        cls.mentoree_skill_2 = TagFactory()

        cls.other_skill = TagFactory()

        for user_type, user in cls.users.items():
            if user_type == "other":
                SkillFactory(user=user, tag=cls.mentor_skill_1)
                SkillFactory(user=user, tag=cls.mentor_skill_2)
                SkillFactory(user=user, tag=cls.mentoree_skill_1)
                SkillFactory(user=user, tag=cls.mentoree_skill_2)
                SkillFactory(user=user, tag=cls.other_skill)
            elif user_type == "public_public_2":
                SkillFactory(user=user, tag=cls.mentor_skill_1)
                SkillFactory(user=user, tag=cls.mentor_skill_2, can_mentor=True)
                SkillFactory(user=user, tag=cls.mentoree_skill_1)
                SkillFactory(user=user, tag=cls.mentoree_skill_2, needs_mentor=True)
                SkillFactory(user=user, tag=cls.other_skill)
            else:
                SkillFactory(user=user, tag=cls.mentor_skill_1, can_mentor=True)
                SkillFactory(user=user, tag=cls.mentor_skill_2, can_mentor=True)
                SkillFactory(user=user, tag=cls.mentoree_skill_1, needs_mentor=True)
                SkillFactory(user=user, tag=cls.mentoree_skill_2, needs_mentor=True)
                SkillFactory(user=user, tag=cls.other_skill)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, 1, 2),
            (TestRoles.DEFAULT, 1, 2),
            (TestRoles.SUPERADMIN, 8, 9),
            (TestRoles.ORG_ADMIN, 8, 9),
            (TestRoles.ORG_FACILITATOR, 8, 9),
            (TestRoles.ORG_USER, 3, 4),
        ]
    )
    def test_retrieve_mentored_skills(self, role, skill_1_mentors, skill_2_mentors):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationMentorship-mentored-skill", args=(organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0]["id"], self.mentor_skill_2.id)
        self.assertEqual(content[0]["mentors_count"], skill_2_mentors)
        self.assertEqual(content[1]["id"], self.mentor_skill_1.id)
        self.assertEqual(content[1]["mentors_count"], skill_1_mentors)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, 1, 2),
            (TestRoles.DEFAULT, 1, 2),
            (TestRoles.SUPERADMIN, 8, 9),
            (TestRoles.ORG_ADMIN, 8, 9),
            (TestRoles.ORG_FACILITATOR, 8, 9),
            (TestRoles.ORG_USER, 3, 4),
        ]
    )
    def test_retrieve_mentoree_skills(self, role, skill_1_mentorees, skill_2_mentorees):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationMentorship-mentoree-skill", args=(organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0]["id"], self.mentoree_skill_2.id)
        self.assertEqual(content[0]["mentorees_count"], skill_2_mentorees)
        self.assertEqual(content[1]["id"], self.mentoree_skill_1.id)
        self.assertEqual(content[1]["mentorees_count"], skill_1_mentorees)
