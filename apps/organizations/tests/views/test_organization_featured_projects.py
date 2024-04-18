from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class OrganizationFeaturedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = ProjectFactory.create_batch(3, organizations=[cls.organization])
        cls.projects = {
            "public": ProjectFactory(
                publication_status=Project.PublicationStatus.PUBLIC,
                organizations=[cls.organization],
            ),
            "private": ProjectFactory(
                publication_status=Project.PublicationStatus.PRIVATE,
                organizations=[cls.organization],
            ),
            "org": ProjectFactory(
                publication_status=Project.PublicationStatus.ORG,
                organizations=[cls.organization],
            ),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_add_featured_project(self, role, expected_code):
        organization = self.organization
        projects = self.projects
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {"featured_projects_ids": [p.pk for p in projects.values()]}
        response = self.client.post(
            reverse(
                "Organization-add-featured-project",
                args=([organization.code]),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            featured_projects = [
                project.id for project in organization.featured_projects.all()
            ]
            for project in projects.values():
                self.assertIn(project.id, featured_projects)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_remove_featured_project(self, role, expected_code):
        organization = self.organization
        projects = self.projects
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {"featured_projects_ids": [p.pk for p in projects.values()]}
        response = self.client.post(
            reverse(
                "Organization-remove-featured-project",
                args=([organization.code]),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for project in projects.values():
                self.assertNotIn(project, organization.featured_projects.all())

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org")),
        ]
    )
    def test_retrieve_featured_projects(self, role, retrieved_projects):
        organization = self.organization
        projects = self.projects
        organization.featured_projects.add(*projects.values())
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Organization-featured-project", args=([organization.code]))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertEqual(
            {p["id"] for p in content},
            {projects[p].id for p in retrieved_projects},
        )
