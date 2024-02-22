from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.models import UserEmbedding
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class UserRecommendationTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        other_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC
        )
        UserEmbeddingFactory(
            item=other_user, embedding=[*1024 * [1.0]], is_visible=True
        )
        public_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
        )
        UserEmbeddingFactory(
            item=public_user, embedding=[*768 * [0.0], *256 * [1.0]], is_visible=True
        )
        private_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
            groups=[cls.organization.get_users()],
        )
        UserEmbeddingFactory(
            item=private_user, embedding=[*512 * [0.0], *512 * [1.0]], is_visible=True
        )
        org_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
            groups=[cls.organization.get_users()],
        )
        UserEmbeddingFactory(
            item=org_user, embedding=[*256 * [0.0], *768 * [1.0]], is_visible=True
        )
        cls.users = {
            "other": other_user,
            "public": public_user,
            "private": private_user,
            "org": org_user,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public"]),
            (TestRoles.DEFAULT, ["public"]),
            (TestRoles.SUPERADMIN, ["org", "private", "public"]),
            (TestRoles.ORG_ADMIN, ["org", "private", "public"]),
            (TestRoles.ORG_FACILITATOR, ["org", "private", "public"]),
            (TestRoles.ORG_USER, ["org", "public"]),
        ]
    )
    def test_get_recommended_users(self, role, retrieved_users):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        if user:
            UserEmbeddingFactory(item=user, embedding=[*1024 * [1.0]], is_visible=True)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("RecommendedUsers-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_users))
        self.assertListEqual(
            [user["id"] for user in content],
            [self.users[user].id for user in retrieved_users],
        )

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_get_recommended_users_create_embedding_vector(
        self, mocked_embeddings, mocked_chat
    ):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        embedding = UserEmbeddingFactory(item=user)
        self.assertIsNone(embedding.embedding)
        messages = [faker.sentence() for _ in range(3)]
        vector = [*1024 * [1.0]]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        response = self.client.get(
            reverse("RecommendedUsers-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        embedding.refresh_from_db()
        self.assertListEqual(list(embedding.embedding), vector)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertListEqual(
            [user["id"] for user in content],
            [self.users[user].id for user in ["org", "private", "public"]],
        )

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_get_recommended_users_create_embedding_object(
        self, mocked_embeddings, mocked_chat
    ):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        self.assertFalse(UserEmbedding.objects.filter(item=user).exists())
        messages = [faker.sentence() for _ in range(3)]
        vector = [*1024 * [1.0]]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        response = self.client.get(
            reverse("RecommendedUsers-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        embedding = UserEmbedding.objects.filter(item=user)
        self.assertTrue(embedding.exists())
        self.assertListEqual(list(embedding.get().embedding), vector)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertListEqual(
            [user["id"] for user in content],
            [self.users[user].id for user in ["org", "private", "public"]],
        )


class ProjectRecommendationTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.other_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        ProjectEmbeddingFactory(
            item=cls.other_project, embedding=[*1024 * [1.0]], is_visible=True
        )
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
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
        ProjectEmbeddingFactory(
            item=cls.private_project,
            embedding=[*512 * [0.0], *512 * [1.0]],
            is_visible=True,
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
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
        ProjectEmbeddingFactory(
            item=cls.member_project, embedding=[*1024 * [1.0]], is_visible=True
        )
        cls.projects = {
            "other": cls.other_project,
            "public": cls.public_project,
            "private": cls.private_project,
            "org": cls.org_project,
            "member": cls.member_project,
        }

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
    def test_get_recommended_projects(self, role, retrieved_projects):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        if user:
            UserEmbeddingFactory(item=user, embedding=[*1024 * [1.0]], is_visible=True)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("RecommendedProjects-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertListEqual(
            [project["id"] for project in content],
            [self.projects[project].id for project in retrieved_projects],
        )

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_get_recommended_projects_create_embedding_vector(
        self, mocked_embeddings, mocked_chat
    ):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        embedding = UserEmbeddingFactory(item=user)
        self.assertIsNone(embedding.embedding)
        messages = [faker.sentence() for _ in range(3)]
        vector = [*1024 * [1.0]]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        response = self.client.get(
            reverse("RecommendedProjects-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        embedding.refresh_from_db()
        self.assertListEqual(list(embedding.embedding), vector)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertListEqual(
            [project["id"] for project in content],
            [
                self.projects[project].id
                for project in ["member", "org", "private", "public"]
            ],
        )

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_get_recommended_projects_create_embedding_object(
        self, mocked_embeddings, mocked_chat
    ):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        self.assertFalse(UserEmbedding.objects.filter(item=user).exists())
        messages = [faker.sentence() for _ in range(3)]
        vector = [*1024 * [1.0]]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        response = self.client.get(
            reverse("RecommendedProjects-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        embedding = UserEmbedding.objects.filter(item=user)
        self.assertTrue(embedding.exists())
        self.assertListEqual(list(embedding.get().embedding), vector)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertListEqual(
            [project["id"] for project in content],
            [
                self.projects[project].id
                for project in ["member", "org", "private", "public"]
            ],
        )
