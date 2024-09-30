from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.skills.factories import SkillFactory
from apps.skills.models import Skill
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()

PrivacyChoices = PrivacySettings.PrivacyChoices


class PrivacySettingsFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @staticmethod
    def set_user_privacy_settings(user, privacy):
        # Publication status is tested in test_user_publication_status.py
        user.privacy_settings.publication_status = PrivacyChoices.PUBLIC
        user.privacy_settings.profile_picture = privacy
        user.privacy_settings.skills = privacy
        user.privacy_settings.socials = privacy
        user.privacy_settings.mobile_phone = privacy
        user.privacy_settings.personal_email = privacy
        user.privacy_settings.save()

    def assert_fields_visible(self, user, data):
        self.assertEqual(data["facebook"], user.facebook)
        self.assertEqual(data["twitter"], user.twitter)
        self.assertEqual(data["skype"], user.skype)
        self.assertEqual(data["landline_phone"], user.landline_phone)
        self.assertEqual(data["mobile_phone"], user.mobile_phone)
        self.assertEqual(data["personal_email"], user.personal_email)
        self.assertEqual(data["linkedin"], user.linkedin)
        self.assertEqual(data["medium"], user.medium)
        self.assertEqual(data["website"], user.website)
        self.assertEqual(data["profile_picture"]["id"], user.profile_picture.id)
        self.assertEqual(
            {skill["id"] for skill in data["skills"]},
            {skill.id for skill in user.skills.all()},
        )

    def assert_fields_hidden(self, data):
        self.assertIsNone(data["facebook"])
        self.assertIsNone(data["twitter"])
        self.assertIsNone(data["skype"])
        self.assertIsNone(data["landline_phone"])
        self.assertIsNone(data["mobile_phone"])
        self.assertIsNone(data["personal_email"])
        self.assertIsNone(data["linkedin"])
        self.assertIsNone(data["medium"])
        self.assertIsNone(data["website"])
        self.assertIsNone(data["profile_picture"])
        self.assertEqual(data["skills"], [])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, PrivacyChoices.PUBLIC, True),
            (TestRoles.DEFAULT, PrivacyChoices.PUBLIC, True),
            (TestRoles.OWNER, PrivacyChoices.PUBLIC, True),
            (TestRoles.SUPERADMIN, PrivacyChoices.PUBLIC, True),
            (TestRoles.ORG_ADMIN, PrivacyChoices.PUBLIC, True),
            (TestRoles.ORG_FACILITATOR, PrivacyChoices.PUBLIC, True),
            (TestRoles.ORG_USER, PrivacyChoices.PUBLIC, True),
            (TestRoles.ANONYMOUS, PrivacyChoices.ORGANIZATION, False),
            (TestRoles.DEFAULT, PrivacyChoices.ORGANIZATION, False),
            (TestRoles.OWNER, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.SUPERADMIN, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ORG_ADMIN, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ORG_FACILITATOR, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ORG_USER, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ANONYMOUS, PrivacyChoices.HIDE, False),
            (TestRoles.DEFAULT, PrivacyChoices.HIDE, False),
            (TestRoles.OWNER, PrivacyChoices.HIDE, True),
            (TestRoles.SUPERADMIN, PrivacyChoices.HIDE, True),
            (TestRoles.ORG_ADMIN, PrivacyChoices.HIDE, True),
            (TestRoles.ORG_FACILITATOR, PrivacyChoices.HIDE, False),
            (TestRoles.ORG_USER, PrivacyChoices.HIDE, False),
        ]
    )
    def test_view_fields_retrieve_user(
        self, role, privacy_settings_value, fields_visible
    ):
        organization = self.organization
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        instance.profile_picture = image
        instance.save()
        self.set_user_privacy_settings(instance, privacy_settings_value)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-detail", args=(instance.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if fields_visible:
            self.assert_fields_visible(instance, response.data)
        else:
            self.assert_fields_hidden(response.data)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, PrivacyChoices.PUBLIC, True),
            (TestRoles.DEFAULT, PrivacyChoices.PUBLIC, True),
            (TestRoles.OWNER, PrivacyChoices.PUBLIC, True),
            (TestRoles.SUPERADMIN, PrivacyChoices.PUBLIC, True),
            (TestRoles.ORG_ADMIN, PrivacyChoices.PUBLIC, True),
            (TestRoles.ORG_FACILITATOR, PrivacyChoices.PUBLIC, True),
            (TestRoles.ORG_USER, PrivacyChoices.PUBLIC, True),
            (TestRoles.ANONYMOUS, PrivacyChoices.ORGANIZATION, False),
            (TestRoles.DEFAULT, PrivacyChoices.ORGANIZATION, False),
            (TestRoles.OWNER, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.SUPERADMIN, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ORG_ADMIN, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ORG_FACILITATOR, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ORG_USER, PrivacyChoices.ORGANIZATION, True),
            (TestRoles.ANONYMOUS, PrivacyChoices.HIDE, False),
            (TestRoles.DEFAULT, PrivacyChoices.HIDE, False),
            (TestRoles.OWNER, PrivacyChoices.HIDE, True),
            (TestRoles.SUPERADMIN, PrivacyChoices.HIDE, True),
            (TestRoles.ORG_ADMIN, PrivacyChoices.HIDE, True),
            (TestRoles.ORG_FACILITATOR, PrivacyChoices.HIDE, False),
            (TestRoles.ORG_USER, PrivacyChoices.HIDE, False),
        ]
    )
    def test_view_fields_list_users(self, role, privacy_settings_value, fields_visible):
        organization = self.organization
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        instance.profile_picture = image
        instance.save()
        self.set_user_privacy_settings(instance, privacy_settings_value)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["id"] == instance.id]
        self.assertEqual(len(retrieved_user), 1)
        retrieved_user = retrieved_user[0]
        if fields_visible:
            self.assertIsNotNone(retrieved_user["profile_picture"])
            self.assertEqual(
                retrieved_user["profile_picture"]["id"], instance.profile_picture.id
            )
        else:
            self.assertIsNone(retrieved_user["profile_picture"])
