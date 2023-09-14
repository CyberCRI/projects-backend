import time

from algoliasearch_django import algolia_engine
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.mixins import skipUnlessAlgolia
from apps.misc.factories import WikipediaTagFactory
from apps.misc.models import Language
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


@skipUnlessAlgolia
class ProjectSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.wikipedia_tag = WikipediaTagFactory()
        cls.organization_2 = OrganizationFactory()
        cls.category_2 = ProjectCategoryFactory(organization=cls.organization_2)
        cls.wikipedia_tag_2 = WikipediaTagFactory()
        Project.objects.all().delete()  # Delete projects created by the factories

        cls.public_project = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.public_project.categories.add(cls.category)
        cls.public_project.wikipedia_tags.add(cls.wikipedia_tag)
        cls.public_project_2 = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization_2],
            sdgs=[2],
            language=Language.EN,
        )
        cls.public_project_2.categories.add(cls.category_2)
        cls.public_project_2.wikipedia_tags.add(cls.wikipedia_tag_2)
        cls.private_project = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.private_project.categories.add(cls.category)
        cls.private_project.wikipedia_tags.add(cls.wikipedia_tag)
        cls.org_project = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
            sdgs=[1],
            language=Language.FR,
        )
        cls.org_project.categories.add(cls.category)
        cls.org_project.wikipedia_tags.add(cls.wikipedia_tag)
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
        cls.public_project_2_member = UserFactory()
        cls.public_project_2.members.add(cls.public_project_2_member)
        cls.member = UserFactory()
        cls.member_project.members.add(cls.member)
        algolia_engine.reindex_all(Project)
        time.sleep(10)  # reindexing is asynchronous, wait for it to finish

    def test_search_project_anonymous(self):
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project.id, self.public_project_2.id},
        )

    def test_search_project_authenticated(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project.id, self.public_project_2.id},
        )

    def test_search_project_org_project(self):
        user = UserFactory()
        self.organization.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project.id, self.public_project_2.id, self.org_project.id},
        )

    def test_search_project_org_facilitator(self):
        user = UserFactory()
        self.organization.facilitators.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.public_project_2.id,
                self.org_project.id,
                self.private_project.id,
                self.member_project.id,
            },
        )

    def test_search_project_org_admin(self):
        user = UserFactory()
        self.organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.public_project_2.id,
                self.org_project.id,
                self.private_project.id,
                self.member_project.id,
            },
        )

    def test_search_project_superadmin(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.public_project_2.id,
                self.org_project.id,
                self.private_project.id,
                self.member_project.id,
            },
        )

    def test_search_project_member(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(reverse("ProjectSearch-search", args=("algolia",)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project.id, self.public_project_2.id, self.member_project.id},
        )

    def test_filter_by_organization(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project_2.id},
        )

    def test_filter_by_sdgs(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",)) + "?sdgs=2"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project_2.id},
        )

    def test_filter_by_language(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",)) + "?languages=en"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project_2.id},
        )

    def test_filter_by_categories(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?categories={self.category_2.id}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project_2.id},
        )

    def test_filter_by_wikipedia_tags(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?wikipedia_tags={self.wikipedia_tag_2.wikipedia_qid}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project_2.id},
        )

    def test_filter_by_members(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectSearch-search", args=("algolia",))
            + f"?members={self.public_project_2_member.keycloak_id}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project_2.id},
        )
