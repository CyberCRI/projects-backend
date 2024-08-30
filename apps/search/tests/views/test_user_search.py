import time

from algoliasearch_django import algolia_engine
from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles, skipUnlessAlgolia
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory
from apps.search.models import SearchObject
from apps.search.tasks import update_or_create_user_search_object_task


@skipUnlessAlgolia
class UserSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.no_org_user = UserFactory(
            given_name="algolia",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[2],
            groups=[],
        )
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

        cls.wikipedia_tag_1 = WikipediaTagFactory()
        cls.wikipedia_tag_2 = WikipediaTagFactory()
        SkillFactory(
            user=cls.public_user_1, wikipedia_tag=cls.wikipedia_tag_1, can_mentor=True
        )
        SkillFactory(
            user=cls.public_user_2, wikipedia_tag=cls.wikipedia_tag_2, can_mentor=True
        )
        SkillFactory(
            user=cls.private_user, wikipedia_tag=cls.wikipedia_tag_1, needs_mentor=True
        )
        SkillFactory(
            user=cls.org_user, wikipedia_tag=cls.wikipedia_tag_2, needs_mentor=True
        )
        cls.users = {
            "public_1": cls.public_user_1,
            "public_2": cls.public_user_2,
            "private": cls.private_user,
            "org": cls.org_user,
        }
        # Create search objects manually because celery tasks are not executed in tests
        for user in cls.users.values():
            update_or_create_user_search_object_task(user.pk)
        algolia_engine.reindex_all(SearchObject)
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
        response = self.client.get(
            reverse("Search-search", args=("algolia",)) + "?types=user"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_users))
        self.assertEqual(
            {user["type"] for user in content},
            {SearchObject.SearchObjectType.USER for _ in retrieved_users},
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content},
            {self.users[user].id for user in retrieved_users},
        )

    def test_filter_by_organization(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + "?types=user"
            + f"&organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content}, {self.public_user_2.id}
        )

    def test_filter_by_sdgs(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",)) + "?types=user" + "&sdgs=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content}, {self.public_user_2.id}
        )

    def test_filter_by_skills(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + "?types=user"
            + f"&skills={self.skill_2.wikipedia_tag.wikipedia_qid}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content}, {self.public_user_2.id}
        )

    def test_filter_can_mentor(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + "?types=user"
            + "&can_mentor=true"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content},
            {self.public_user_1.id, self.public_user_2.id},
        )

    def test_filter_needs_mentor(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + "?types=user"
            + "&needs_mentor=true"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content},
            {self.private_user.id, self.org_user.id},
        )

    def test_filter_can_mentor_on(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + "?types=user"
            + f"&can_mentor_on={self.wikipedia_tag_1.wikipedia_qid},{self.wikipedia_tag_2.wikipedia_qid}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content},
            {self.public_user_1.id, self.public_user_2.id},
        )

    def test_filter_needs_mentor_on(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + "?types=user"
            + f"&needs_mentor_on={self.wikipedia_tag_1.wikipedia_qid},{self.wikipedia_tag_2.wikipedia_qid}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["type"] for user in content}, {SearchObject.SearchObjectType.USER}
        )
        self.assertSetEqual(
            {user["user"]["id"] for user in content},
            {self.private_user.id, self.org_user.id},
        )
