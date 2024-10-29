from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectScoreFactory
from apps.projects.models import Project
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class RecommendedProjectsTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.other_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        ProjectScoreFactory(
            project=cls.other_project,
            completeness=10.0,
            popularity=10.0,
            activity=10.0,
            score=30.0,
        )
        ProjectEmbeddingFactory(
            item=cls.other_project, embedding=[*1024 * [1.0]], is_visible=True
        )
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        ProjectScoreFactory(
            project=cls.public_project,
            completeness=3.0,
            popularity=3.0,
            activity=3.0,
            score=9.0,
        )
        ProjectEmbeddingFactory(
            item=cls.public_project,
            embedding=[*768 * [0.0], *256 * [1.0]],
            is_visible=True,
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        ProjectScoreFactory(
            project=cls.private_project,
            completeness=1.0,
            popularity=1.0,
            activity=1.0,
            score=3.0,
        )
        ProjectEmbeddingFactory(
            item=cls.private_project,
            embedding=[*512 * [0.0], *512 * [1.0]],
            is_visible=True,
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        ProjectScoreFactory(
            project=cls.org_project,
            completeness=1.0,
            popularity=1.0,
            activity=1.0,
            score=3.0,
        )
        ProjectEmbeddingFactory(
            item=cls.org_project,
            embedding=[*256 * [0.0], *768 * [1.0]],
            is_visible=True,
        )
        cls.member_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        ProjectScoreFactory(
            project=cls.member_project,
            completeness=1.0,
            popularity=1.0,
            activity=1.0,
            score=3.0,
        )
        ProjectEmbeddingFactory(
            item=cls.member_project,
            embedding=[*128 * [0.0], *896 * [1.0]],
            is_visible=True,
        )
        cls.project = ProjectFactory(
            organizations=[cls.organization],
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        ProjectScoreFactory(
            project=cls.project,
            completeness=2.0,
            popularity=2.0,
            activity=2.0,
            score=6.0,
        )
        ProjectEmbeddingFactory(
            item=cls.project,
            embedding=[*1024 * [1.0]],
            is_visible=True,
        )
        cls.projects = {
            "other": cls.other_project,
            "main": cls.project,
            "public": cls.public_project,
            "private": cls.private_project,
            "org": cls.org_project,
            "member": cls.member_project,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public", "main"]),
            (TestRoles.DEFAULT, ["main", "public"]),
            (TestRoles.SUPERADMIN, ["main", "member", "org", "private", "public"]),
            (TestRoles.ORG_ADMIN, ["main", "member", "org", "private", "public"]),
            (TestRoles.ORG_FACILITATOR, ["main", "member", "org", "private", "public"]),
            (TestRoles.ORG_USER, ["main", "org", "public"]),
            (TestRoles.PROJECT_OWNER, ["main", "public"]),
            (TestRoles.PROJECT_REVIEWER, ["main", "public"]),
            (TestRoles.PROJECT_MEMBER, ["main", "public"]),
        ]
    )
    def test_user_recommended_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        if role != TestRoles.ANONYMOUS:
            UserEmbeddingFactory(item=user, embedding=[*1024 * [1.0]], is_visible=True)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "RecommendedProjects-for-user",
                args=(self.organization.code,),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertListEqual(
            [project["id"] for project in content],
            [self.projects[project].id for project in retrieved_projects],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public"]),
            (TestRoles.DEFAULT, ["public"]),
            (TestRoles.SUPERADMIN, ["member", "org", "private", "public"]),
            (TestRoles.ORG_ADMIN, ["member", "org", "private", "public"]),
            (TestRoles.ORG_FACILITATOR, ["member", "org", "private", "public"]),
            (TestRoles.ORG_USER, ["org", "public"]),
            (TestRoles.PROJECT_OWNER, ["member", "public"]),
            (TestRoles.PROJECT_REVIEWER, ["member", "public"]),
            (TestRoles.PROJECT_MEMBER, ["member", "public"]),
        ]
    )
    def test_project_recommended_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "RecommendedProjects-for-project",
                args=(self.organization.code, self.project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertListEqual(
            [project["id"] for project in content],
            [self.projects[project].id for project in retrieved_projects],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public"]),
            (TestRoles.DEFAULT, ["public"]),
            (TestRoles.SUPERADMIN, ["member", "org", "private", "public"]),
            (TestRoles.ORG_ADMIN, ["member", "org", "private", "public"]),
            (TestRoles.ORG_FACILITATOR, ["member", "org", "private", "public"]),
            (TestRoles.ORG_USER, ["org", "public"]),
            (TestRoles.PROJECT_OWNER, ["member", "public"]),
            (TestRoles.PROJECT_REVIEWER, ["member", "public"]),
            (TestRoles.PROJECT_MEMBER, ["member", "public"]),
        ]
    )
    def test_project_recommended_random_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "RecommendedProjects-random-for-project",
                args=(self.organization.code, self.project.id),
            )
            + "?count=1"
            + "&pool=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), 1)
        self.assertIn(
            content[0]["id"],
            [self.projects[project].id for project in retrieved_projects[:2]],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public", "main"]),
            (TestRoles.DEFAULT, ["main", "public"]),
            (TestRoles.SUPERADMIN, ["main", "member", "org", "private", "public"]),
            (TestRoles.ORG_ADMIN, ["main", "member", "org", "private", "public"]),
            (TestRoles.ORG_FACILITATOR, ["main", "member", "org", "private", "public"]),
            (TestRoles.ORG_USER, ["main", "org", "public"]),
            (TestRoles.PROJECT_OWNER, ["main", "public"]),
            (TestRoles.PROJECT_REVIEWER, ["main", "public"]),
            (TestRoles.PROJECT_MEMBER, ["main", "public"]),
        ]
    )
    def test_user_recommended_random_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        if role != TestRoles.ANONYMOUS:
            UserEmbeddingFactory(item=user, embedding=[*1024 * [1.0]], is_visible=True)
        response = self.client.get(
            reverse(
                "RecommendedProjects-random-for-user",
                args=(self.organization.code,),
            )
            + "?count=1"
            + "&pool=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), 1)
        self.assertIn(
            content[0]["id"],
            [self.projects[project].id for project in retrieved_projects[:2]],
        )

    def test_project_recommended_projects_multiple_lookups(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(
            reverse(
                "RecommendedProjects-for-project",
                args=(self.organization.code, self.project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertSetEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.org_project.id,
                self.member_project.id,
                self.private_project.id,
            },
        )
        response = self.client.get(
            reverse(
                "RecommendedProjects-for-project",
                args=(self.organization.code, self.project.slug),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertSetEqual(
            {project["id"] for project in content},
            {
                self.public_project.id,
                self.org_project.id,
                self.member_project.id,
                self.private_project.id,
            },
        )
