from django.urls import reverse
from faker import Faker
from parameterized import parameterized

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import PrivacySettings, Skill
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

    @staticmethod
    def assert_fields_visible(user, data):
        assert data["facebook"] == user.facebook
        assert data["twitter"] == user.twitter
        assert data["skype"] == user.skype
        assert data["landline_phone"] == user.landline_phone
        assert data["mobile_phone"] == user.mobile_phone
        assert data["personal_email"] == user.personal_email
        assert data["linkedin"] == user.linkedin
        assert data["medium"] == user.medium
        assert data["website"] == user.website
        assert {skill["id"] for skill in data["skills"]} == {
            skill.id for skill in user.skills.filter(type=Skill.SkillType.SKILL)
        }
        assert {skill["id"] for skill in data["hobbies"]} == {
            skill.id for skill in user.skills.filter(type=Skill.SkillType.HOBBY)
        }
        assert data["profile_picture"]["id"] == user.profile_picture.id

    @staticmethod
    def assert_fields_hidden(data):
        assert data["facebook"] is None
        assert data["twitter"] is None
        assert data["skype"] is None
        assert data["landline_phone"] is None
        assert data["mobile_phone"] is None
        assert data["personal_email"] is None
        assert data["linkedin"] is None
        assert data["medium"] is None
        assert data["website"] is None
        assert data["skills"] == []
        assert data["hobbies"] == []
        assert data["profile_picture"] is None

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
            role, organization=organization, owned_instance=instance
        )
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        instance.profile_picture = image
        instance.save()
        self.set_user_privacy_settings(instance, privacy_settings_value)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[instance.keycloak_id])
        )
        assert response.status_code == 200
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
            role, organization=organization, owned_instance=instance
        )
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=instance, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        instance.profile_picture = image
        instance.save()
        self.set_user_privacy_settings(instance, privacy_settings_value)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [
            u for u in content if u["keycloak_id"] == instance.keycloak_id
        ]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        if fields_visible:
            assert (
                retrieved_user["profile_picture"]["id"] == instance.profile_picture.id
            )
        else:
            assert retrieved_user["profile_picture"] is None
