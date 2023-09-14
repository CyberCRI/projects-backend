import time

from algoliasearch_django import algolia_engine
from django.urls import reverse

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.mixins import skipUnlessAlgolia
from apps.organizations.factories import OrganizationFactory


@skipUnlessAlgolia
class UserSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        ProjectUser.objects.all().delete()  # Delete users created by the factories

        cls.public_user = UserFactory(
            given_name="algolia",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.public_user)
        cls.public_user_2 = UserFactory(
            given_name="algolia",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[2],
            groups=[cls.organization_2.get_users()],
        )
        cls.skill_2 = SkillFactory(user=cls.public_user_2)
        cls.private_user = UserFactory(
            given_name="algolia",
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.private_user)
        cls.org_user = UserFactory(
            given_name="algolia",
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.org_user)
        algolia_engine.reindex_all(ProjectUser)
        time.sleep(10)  # reindexing is asynchronous, wait for it to finish

    def test_search_user_anonymous(self):
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.public_user_2.id},
        )

    def test_search_user_authenticated(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.public_user_2.id},
        )

    def test_search_user_org_user(self):
        user = UserFactory()
        self.organization.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.public_user_2.id, self.org_user.id},
        )

    def test_search_user_org_facilitator(self):
        user = UserFactory()
        self.organization.facilitators.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {user["id"] for user in content},
            {
                self.public_user.id,
                self.public_user_2.id,
                self.org_user.id,
                self.private_user.id,
            },
        )

    def test_search_user_org_admin(self):
        user = UserFactory()
        self.organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {user["id"] for user in content},
            {
                self.public_user.id,
                self.public_user_2.id,
                self.org_user.id,
                self.private_user.id,
            },
        )

    def test_search_user_superadmin(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {user["id"] for user in content},
            {
                self.public_user.id,
                self.public_user_2.id,
                self.org_user.id,
                self.private_user.id,
            },
        )

    def test_filter_by_organization(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("UserSearch-search", args=("algolia",))
            + f"?organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user_2.id},
        )

    def test_filter_by_sdgs(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("UserSearch-search", args=("algolia",)) + "?sdgs=2"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user_2.id},
        )

    def test_filter_by_skills(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("UserSearch-search", args=("algolia",))
            + f"?skills={self.skill_2.wikipedia_tag.wikipedia_qid}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user_2.id},
        )
