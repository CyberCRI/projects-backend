import time

from algoliasearch_django import algolia_engine
from django.urls import reverse
from parameterized import parameterized

from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.commons.test.mixins import skipUnlessAlgolia
from apps.misc.factories import TagFactory, WikipediaTagFactory
from apps.misc.models import Language
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


@skipUnlessAlgolia
class ProjectSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.wikipedia_tag = WikipediaTagFactory()
        cls.organization_tag = TagFactory(organization=cls.organization)
        cls.organization_2 = OrganizationFactory()
        cls.category_2 = ProjectCategoryFactory(organization=cls.organization_2)
        cls.wikipedia_tag_2 = WikipediaTagFactory()
        cls.organization_tag_2 = TagFactory(organization=cls.organization_2)
        Project.objects.all().delete()  # Delete projects created by the factories

        cls.public_project_1 = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.public_project_1.categories.add(cls.category)
        cls.public_project_1.wikipedia_tags.add(cls.wikipedia_tag)
        cls.public_project_1.organization_tags.add(cls.organization_tag)
        cls.public_project_2 = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization_2],
            sdgs=[2],
            language=Language.EN,
        )
        cls.public_project_2.categories.add(cls.category_2)
        cls.public_project_2.wikipedia_tags.add(cls.wikipedia_tag_2)
        cls.public_project_2.organization_tags.add(cls.organization_tag_2)
        cls.private_project = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.private_project.categories.add(cls.category)
        cls.private_project.wikipedia_tags.add(cls.wikipedia_tag)
        cls.private_project.organization_tags.add(cls.organization_tag)
        cls.org_project = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.org_project.categories.add(cls.category)
        cls.org_project.wikipedia_tags.add(cls.wikipedia_tag)
        cls.org_project.organization_tags.add(cls.organization_tag)
        cls.member_project = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.member_project.categories.add(cls.category)
        cls.member_project.wikipedia_tags.add(cls.wikipedia_tag)
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
            "member": cls.member_project,
        }
        algolia_engine.reindex_all(Project)
        time.sleep(10)  # reindexing is asynchronous, wait for it to finish

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public_1", "public_2")),
            (TestRoles.DEFAULT, ("public_1", "public_2")),
            (
                TestRoles.SUPERADMIN,
                ("public_1", "public_2", "private", "org", "member"),
            ),
            (TestRoles.ORG_ADMIN, ("public_1", "public_2", "private", "org", "member")),
            (
                TestRoles.ORG_FACILITATOR,
                ("public_1", "public_2", "private", "org", "member"),
            ),
            (TestRoles.ORG_USER, ("public_1", "public_2", "org")),
            (TestRoles.PROJECT_MEMBER, ("public_1", "public_2", "member")),
        ]
    )
    def test_search_project(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == len(retrieved_projects)
        assert {project["id"] for project in content} == {
            self.projects[project].id for project in retrieved_projects
        }

    def test_filter_by_organization(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?organizations={self.organization_2.code}"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}

    def test_filter_by_sdgs(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",)) + "?sdgs=2"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}

    def test_filter_by_language(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",)) + "?languages=en"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}

    def test_filter_by_categories(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?categories={self.category_2.id}"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}

    def test_filter_by_wikipedia_tags(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?wikipedia_tags={self.wikipedia_tag_2.wikipedia_qid}"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}

    def test_filter_by_organization_tags(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?organization_tags={self.organization_tag_2.id}"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}

    def test_filter_by_members(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?members={self.public_project_2_member.id}"
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 1
        assert {project["id"] for project in content} == {self.public_project_2.id}
