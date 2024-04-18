from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class ProjectPublicationStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
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
        cls.projects = {
            "public": cls.public_project,
            "private": cls.private_project,
            "org": cls.org_project,
            "member": cls.member_project,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "member")),
            (TestRoles.PROJECT_OWNER, ("public", "member")),
            (TestRoles.PROJECT_REVIEWER, ("public", "member")),
        ]
    )
    def test_retrieve_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        for publication_status, project in self.projects.items():
            response = self.client.get(reverse("Project-detail", args=(project.id,)))
            if publication_status in retrieved_projects:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.json()["id"], project.id)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "member")),
            (TestRoles.PROJECT_OWNER, ("public", "member")),
            (TestRoles.PROJECT_REVIEWER, ("public", "member")),
        ]
    )
    def test_list_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertSetEqual(
            {project["id"] for project in content},
            {
                self.projects[publication_status].id
                for publication_status in retrieved_projects
            },
        )
