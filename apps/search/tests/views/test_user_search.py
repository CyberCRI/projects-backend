from unittest.mock import patch

from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.search.models import SearchObject
from apps.search.testcases import SearchTestCaseMixin
from apps.skills.factories import SkillFactory, TagFactory


class UserSearchTestCase(JwtAPITestCase, SearchTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.no_org_user = UserFactory(
            given_name="opensearch",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[1],
            groups=[],
        )
        cls.public_user_1 = UserFactory(
            given_name="opensearch",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.public_user_1)
        cls.public_user_2 = UserFactory(
            given_name="opensearch",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            sdgs=[2],
            groups=[cls.organization_2.get_users()],
        )
        cls.skill_2 = SkillFactory(user=cls.public_user_2)
        cls.private_user = UserFactory(
            given_name="opensearch",
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.private_user)
        cls.org_user = UserFactory(
            given_name="opensearch",
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
            sdgs=[1],
            groups=[cls.organization.get_users()],
        )
        SkillFactory(user=cls.org_user)

        cls.tag_1 = TagFactory()
        cls.tag_2 = TagFactory()
        SkillFactory(user=cls.public_user_1, tag=cls.tag_1, can_mentor=True)
        SkillFactory(user=cls.public_user_2, tag=cls.tag_2, can_mentor=True)
        SkillFactory(user=cls.private_user, tag=cls.tag_1, needs_mentor=True)
        SkillFactory(user=cls.org_user, tag=cls.tag_2, needs_mentor=True)
        cls.users = {
            "public_1": cls.public_user_1,
            "public_2": cls.public_user_2,
            "private": cls.private_user,
            "org": cls.org_user,
            "no_org": cls.no_org_user,
        }
        cls.search_objects = {
            key: SearchObject.objects.create(
                type=SearchObject.SearchObjectType.USER, user=value
            )
            for key, value in cls.users.items()
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public_1", "public_2", "no_org")),
            (TestRoles.DEFAULT, ("public_1", "public_2", "no_org")),
            (TestRoles.OWNER, ("public_1", "public_2", "private", "org", "no_org")),
            (
                TestRoles.SUPERADMIN,
                ("public_1", "public_2", "private", "org", "no_org"),
            ),
            (TestRoles.ORG_ADMIN, ("public_1", "public_2", "private", "org", "no_org")),
            (
                TestRoles.ORG_FACILITATOR,
                ("public_1", "public_2", "private", "org", "no_org"),
            ),
            (TestRoles.ORG_USER, ("public_1", "public_2", "org", "no_org")),
            (TestRoles.ORG_VIEWER, ("public_1", "public_2", "org", "no_org")),
        ]
    )
    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_search_user(self, role, retrieved_users, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects[user] for user in retrieved_users],
            query="opensearch",
        )
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.private_user
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",)) + "?types=user"
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_by_organization(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_by_sdgs(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",)) + "?types=user" + "&sdgs=2"
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_by_skills(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=user"
            + f"&skills={self.skill_2.tag.id}"
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_can_mentor(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[
                self.search_objects["public_2"],
                self.search_objects["public_1"],
            ],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_needs_mentor(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["org"], self.search_objects["private"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_can_mentor_on(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[
                self.search_objects["public_2"],
                self.search_objects["public_1"],
            ],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=user"
            + f"&can_mentor_on={self.tag_1.id},{self.tag_2.id}"
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

    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_filter_needs_mentor_on(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["org"], self.search_objects["private"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=user"
            + f"&needs_mentor_on={self.tag_1.id},{self.tag_2.id}"
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
