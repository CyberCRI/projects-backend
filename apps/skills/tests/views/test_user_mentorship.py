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


class UserMentorshipTestCase(JwtAPITestCase):
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
            else:
                SkillFactory(user=user, tag=cls.mentor_skill_1, can_mentor=True)
                SkillFactory(user=user, tag=cls.mentor_skill_2, can_mentor=True)
                SkillFactory(user=user, tag=cls.mentoree_skill_1, needs_mentor=True)
                SkillFactory(user=user, tag=cls.mentoree_skill_2, needs_mentor=True)
                SkillFactory(user=user, tag=cls.other_skill)

    @parameterized.expand(
        [
            (TestRoles.DEFAULT, ("public_public",)),
            (
                TestRoles.SUPERADMIN,
                (
                    "public_public",
                    "private_public",
                    "org_public",
                    "public_private",
                    "private_private",
                    "org_private",
                    "public_org",
                    "private_org",
                ),
            ),
            (
                TestRoles.ORG_ADMIN,
                (
                    "public_public",
                    "private_public",
                    "org_public",
                    "public_private",
                    "private_private",
                    "org_private",
                    "public_org",
                    "private_org",
                ),
            ),
            (
                TestRoles.ORG_FACILITATOR,
                (
                    "public_public",
                    "private_public",
                    "org_public",
                    "public_private",
                    "private_private",
                    "org_private",
                    "public_org",
                    "private_org",
                ),
            ),
            (TestRoles.ORG_USER, ("public_public", "org_public", "public_org")),
            (TestRoles.ORG_VIEWER, ("public_public", "org_public", "public_org")),
        ]
    )
    def test_retrieve_mentor_candidates(self, role, mentors):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        SkillFactory(user=user, tag=self.mentor_skill_1, needs_mentor=True)
        SkillFactory(user=user, tag=self.mentor_skill_2, needs_mentor=True)
        SkillFactory(user=user, tag=self.other_skill, needs_mentor=True)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "UserMentorship-mentor-candidate", args=(organization.code, user.id)
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(mentors))
        self.assertSetEqual(
            {user["id"] for user in content},
            {self.users[mentor].id for mentor in mentors},
        )
        for user in content:
            self.assertSetEqual(
                {skill["tag"]["id"] for skill in user["can_mentor_on"]},
                {self.mentor_skill_1.id, self.mentor_skill_2.id},
            )

    @parameterized.expand(
        [
            (TestRoles.DEFAULT, ("public_public",)),
            (
                TestRoles.SUPERADMIN,
                (
                    "public_public",
                    "private_public",
                    "org_public",
                    "public_private",
                    "private_private",
                    "org_private",
                    "public_org",
                    "private_org",
                ),
            ),
            (
                TestRoles.ORG_ADMIN,
                (
                    "public_public",
                    "private_public",
                    "org_public",
                    "public_private",
                    "private_private",
                    "org_private",
                    "public_org",
                    "private_org",
                ),
            ),
            (
                TestRoles.ORG_FACILITATOR,
                (
                    "public_public",
                    "private_public",
                    "org_public",
                    "public_private",
                    "private_private",
                    "org_private",
                    "public_org",
                    "private_org",
                ),
            ),
            (TestRoles.ORG_USER, ("public_public", "org_public", "public_org")),
            (TestRoles.ORG_VIEWER, ("public_public", "org_public", "public_org")),
        ]
    )
    def test_retrieve_mentoree_candidates(self, role, mentorees):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        SkillFactory(user=user, tag=self.mentoree_skill_1, can_mentor=True)
        SkillFactory(user=user, tag=self.mentoree_skill_2, can_mentor=True)
        SkillFactory(user=user, tag=self.other_skill, can_mentor=True)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "UserMentorship-mentoree-candidate", args=(organization.code, user.id)
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(mentorees))
        self.assertSetEqual(
            {user["id"] for user in content},
            {self.users[mentoree].id for mentoree in mentorees},
        )
        for user in content:
            self.assertSetEqual(
                {skill["tag"]["id"] for skill in user["needs_mentor_on"]},
                {
                    self.mentoree_skill_1.id,
                    self.mentoree_skill_2.id,
                },
            )
