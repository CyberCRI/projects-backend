from django.urls import reverse

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import PrivacySettings, Skill
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.mixins import ImageStorageTestCaseMixin
from apps.organizations.factories import OrganizationFactory


class UserPrivacySettingsRetrieveTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @staticmethod
    def set_all_settings(user, privacy):
        # Publication status is tested in test_user_publication_status.py
        user.privacy_settings.publication_status = PrivacySettings.PrivacyChoices.PUBLIC
        user.privacy_settings.profile_picture = privacy
        user.privacy_settings.skills = privacy
        user.privacy_settings.socials = privacy
        user.privacy_settings.mobile_phone = privacy
        user.privacy_settings.personal_email = privacy
        user.privacy_settings.save()

    @staticmethod
    def assert_fields_visible(user, data):
        assert all(
            key in data
            for key in [
                "profile_picture",
                "skills",
                "hobbies",
                "facebook",
                "mobile_phone",
                "linkedin",
                "medium",
                "website",
                "personal_email",
                "skype",
                "landline_phone",
                "twitter",
            ]
        )
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
        assert all(
            key in data
            for key in [
                "profile_picture",
                "skills",
                "hobbies",
                "facebook",
                "mobile_phone",
                "linkedin",
                "medium",
                "website",
                "personal_email",
                "skype",
                "landline_phone",
                "twitter",
            ]
        )
        assert data["skills"] == []
        assert data["hobbies"] == []
        assert data["profile_picture"] is None
        assert data["facebook"] is None
        assert data["twitter"] is None
        assert data["skype"] is None
        assert data["landline_phone"] is None
        assert data["mobile_phone"] is None
        assert data["personal_email"] is None
        assert data["linkedin"] is None
        assert data["medium"] is None
        assert data["website"] is None

    def test_settings_public_anonymous(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_private_anonymous(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_hidden(response.data)

    def test_settings_org_anonymous(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_hidden(response.data)

    def test_settings_org_own_profile(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_public_own_profile(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_private_own_profile(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_org_no_permission(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_hidden(response.data)

    def test_settings_public_no_permission(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_private_no_permission(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_hidden(response.data)

    def test_settings_org_superadmin(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_private_superadmin(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_org_same_org(self):
        user = UserFactory()
        org_user = UserFactory()
        organization = OrganizationFactory()
        organization.users.add(user, org_user)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(org_user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_visible(user, response.data)

    def test_settings_private_same_org(self):
        user = UserFactory()
        org_user = UserFactory()
        organization = OrganizationFactory()
        organization.users.add(user, org_user)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(org_user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200
        self.assert_fields_hidden(response.data)


class UserPrivacySettingsListTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @staticmethod
    def set_all_settings(user, privacy):
        user.privacy_settings.profile_picture = privacy
        user.privacy_settings.save()

    @staticmethod
    def assert_fields_visible(user, data):
        assert data["profile_picture"]["id"] == user.profile_picture.id

    @staticmethod
    def assert_fields_hidden(data):
        assert data["profile_picture"] is None

    def test_settings_public_anonymous(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_private_anonymous(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_hidden(retrieved_user)

    def test_settings_org_anonymous(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_hidden(retrieved_user)

    def test_settings_org_own_profile(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_public_own_profile(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_private_own_profile(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_org_no_permission(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_hidden(retrieved_user)

    def test_settings_public_no_permission(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_private_no_permission(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_hidden(retrieved_user)

    def test_settings_org_superadmin(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_public_superadmin(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.PUBLIC)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_private_superadmin(self):
        user = UserFactory()
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_org_same_org(self):
        user = UserFactory()
        org_user = UserFactory()
        organization = OrganizationFactory()
        organization.users.add(user, org_user)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.ORGANIZATION)
        self.client.force_authenticate(org_user)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_visible(user, retrieved_user)

    def test_settings_private_same_org(self):
        user = UserFactory()
        org_user = UserFactory()
        organization = OrganizationFactory()
        organization.users.add(user, org_user)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.SKILL)
        SkillFactory.create_batch(5, user=user, type=Skill.SkillType.HOBBY)
        image = self.get_test_image()
        user.profile_picture = image
        user.save()
        self.set_all_settings(user, PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(org_user)
        response = self.client.get(reverse("ProjectUser-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        retrieved_user = [u for u in content if u["keycloak_id"] == user.keycloak_id]
        assert len(retrieved_user) == 1
        retrieved_user = retrieved_user[0]
        self.assert_fields_hidden(retrieved_user)
