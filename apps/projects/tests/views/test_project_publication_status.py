from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class ProjectPublicationStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        Project.objects.all().delete()  # Delete projects created by the factories
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.member_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.member = UserFactory()
        cls.member_project.members.add(cls.member)


class AnonymousUserTestCase(ProjectPublicationStatusTestCase):
    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            if project == self.public_project:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content}, {self.public_project.id}
        )


class AuthenticatedUserTestCase(ProjectPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            if project == self.public_project:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {project["id"] for project in content}, {self.public_project.id}
        )


class OrganizationMemberTestCase(ProjectPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()
        cls.organization.users.add(cls.user)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            if project in [self.public_project, self.org_project]:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project.id, self.org_project.id},
        )


class OrganizationFacilitatorTestCase(ProjectPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()
        cls.organization.facilitators.add(cls.user)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            self.assertEqual(response.status_code, 200)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.org_project.id,
                self.private_project.id,
                self.member_project.id,
            },
        )


class OrganizationAdminTestCase(ProjectPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()
        cls.organization.admins.add(cls.user)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            self.assertEqual(response.status_code, 200)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.org_project.id,
                self.private_project.id,
                self.member_project.id,
            },
        )


class SuperAdminTestCase(ProjectPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(
            groups=[get_superadmins_group()],
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            self.assertEqual(response.status_code, 200)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.org_project.id,
                self.private_project.id,
                self.member_project.id,
            },
        )


class ProjectMemberTestCase(ProjectPublicationStatusTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.member)

    def test_retrieve_projects(self):
        for project in [
            self.public_project,
            self.private_project,
            self.org_project,
            self.member_project,
        ]:
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            if project in [self.public_project, self.member_project]:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_projects(self):
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {project["id"] for project in content},
            {self.public_project.id, self.member_project.id},
        )
