import time

from algoliasearch_django import algolia_engine
from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.commons.test.mixins import skipUnlessAlgolia
from apps.organizations.factories import OrganizationFactory


@skipUnlessAlgolia
class UserSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.public_user_1 = UserFactory(
            given_name="algolia",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.public_user_1)
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
        cls.users = {
            "public_1": cls.public_user_1,
            "public_2": cls.public_user_2,
            "private": cls.private_user,
            "org": cls.org_user,
        }
        algolia_engine.reindex_all(ProjectUser)
        time.sleep(10)  # reindexing is asynchronous, wait for it to finish

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public_1", "public_2")),
            (TestRoles.DEFAULT, ("public_1", "public_2")),
            (TestRoles.OWNER, ("public_1", "public_2", "private", "org")),
            (TestRoles.SUPERADMIN, ("public_1", "public_2", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public_1", "public_2", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public_1", "public_2", "private", "org")),
            (TestRoles.ORG_USER, ("public_1", "public_2", "org")),
        ]
    )
    def test_search_user(self, role, retrieved_users):
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.private_user
        )
        self.client.force_authenticate(user)
        response = self.client.get(reverse("UserSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        assert len(content) == len(retrieved_users)
        assert {user["id"] for user in content} == {
            self.users[user].id for user in retrieved_users
        }

    def test_filter_by_organization(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("UserSearch-search", args=("algolia",))
            + f"?organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        assert len(content) == 1
        assert {user["id"] for user in content} == {self.public_user_2.id}

    def test_filter_by_sdgs(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("UserSearch-search", args=("algolia",)) + "?sdgs=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        assert len(content) == 1
        assert {user["id"] for user in content} == {self.public_user_2.id}

    def test_filter_by_skills(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("UserSearch-search", args=("algolia",))
            + f"?skills={self.skill_2.wikipedia_tag.wikipedia_qid}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        assert len(content) == 1
        assert {user["id"] for user in content} == {self.public_user_2.id}
