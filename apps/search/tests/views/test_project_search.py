from unittest.mock import patch

from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.enums import Language
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.search.models import SearchObject
from apps.search.testcases import SearchTestCaseMixin
from apps.skills.factories import TagFactory


class ProjectSearchTestCase(JwtAPITestCase, SearchTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.tag = TagFactory()
        cls.organization_2 = OrganizationFactory()
        cls.category_2 = ProjectCategoryFactory(organization=cls.organization_2)
        cls.tag_2 = TagFactory()
        Project.objects.all().delete()  # Delete projects created by the factories
        cls.no_organization_project = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PUBLIC,
            sdgs=[1],
            language=Language.FR,
            organizations=[cls.organization],
        )
        cls.no_organization_project.organizations.set([])
        cls.public_project_1 = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.public_project_1.categories.add(cls.category)
        cls.public_project_1.tags.add(cls.tag)
        cls.public_project_2 = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization_2],
            sdgs=[2],
            language=Language.EN,
        )
        cls.public_project_2.categories.add(cls.category_2)
        cls.public_project_2.tags.add(cls.tag_2)
        cls.private_project = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.private_project.categories.add(cls.category)
        cls.private_project.tags.add(cls.tag)
        cls.org_project = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.org_project.categories.add(cls.category)
        cls.org_project.tags.add(cls.tag)
        cls.member_project = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.member_project.categories.add(cls.category)
        cls.member_project.tags.add(cls.tag)
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.public_project_2_member = UserFactory()
        cls.public_project_2.members.add(cls.public_project_2_member)
        cls.member = UserFactory()
        cls.member_project.members.add(cls.member)
        cls.projects = {
            "public_1": cls.public_project_1,
            "public_2": cls.public_project_2,
            "private": cls.private_project,
            "org": cls.org_project,
            "no_org": cls.no_organization_project,
            "member": cls.member_project,
        }
        cls.search_objects = {
            key: SearchObject.objects.create(
                type=SearchObject.SearchObjectType.PROJECT, project=value
            )
            for key, value in cls.projects.items()
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public_1", "public_2", "no_org")),
            (TestRoles.DEFAULT, ("public_1", "public_2", "no_org")),
            (
                TestRoles.SUPERADMIN,
                ("public_1", "public_2", "private", "org", "member", "no_org"),
            ),
            (
                TestRoles.ORG_ADMIN,
                ("public_1", "public_2", "private", "org", "member", "no_org"),
            ),
            (
                TestRoles.ORG_FACILITATOR,
                ("public_1", "public_2", "private", "org", "member", "no_org"),
            ),
            (TestRoles.ORG_USER, ("public_1", "public_2", "org", "no_org")),
            (TestRoles.PROJECT_MEMBER, ("public_1", "public_2", "member", "no_org")),
        ]
    )
    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_search_project(self, role, retrieved_projects, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[
                self.search_objects[project] for project in retrieved_projects
            ],
            query="opensearch",
        )
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",)) + "?types=project"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT for _ in retrieved_projects},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.projects[project].id for project in retrieved_projects},
        )

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_filter_by_organization(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=project"
            + f"&organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.public_project_2.id},
        )

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_filter_by_sdgs(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=project"
            + "&sdgs=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.public_project_2.id},
        )

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_filter_by_language(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=project"
            + "&languages=en"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.public_project_2.id},
        )

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_filter_by_categories(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=project"
            + f"&categories={self.category_2.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.public_project_2.id},
        )

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_filter_by_tags(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=project"
            + f"&tags={self.tag_2.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.public_project_2.id},
        )

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_filter_by_members(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=[self.search_objects["public_2"]],
            query="opensearch",
        )
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=project"
            + f"&members={self.public_project_2_member.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["type"] for project in content},
            {SearchObject.SearchObjectType.PROJECT},
        )
        self.assertSetEqual(
            {project["project"]["id"] for project in content},
            {self.public_project_2.id},
        )
