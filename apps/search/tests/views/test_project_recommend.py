import random
from unittest.mock import patch

from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class RecommendProjectsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
        ]
    )
    @patch("algoliasearch.recommend_client.RecommendClient.get_related_products")
    def test_get_similar_projects(self, role, retrieved_projects, mocked):
        hits = [
            {"id": project.id, "_score": round(random.uniform(50, 100), 2)}  # nosec
            for publication_status, project in self.projects.items()
            if publication_status in retrieved_projects
        ]
        hits = sorted(hits, key=lambda x: x["_score"], reverse=True)
        mocked.return_value = {"results": [{"hits": hits}]}
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user=user)
        response = self.client.get(
            reverse("Project-similar", args=(self.project.id,))
            + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertListEqual(
            [p["id"] for p in content],
            [p["id"] for p in hits],
        )
