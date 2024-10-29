from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory, UserScoreFactory
from apps.accounts.models import PrivacySettings
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.models import UserEmbedding
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class UserRecommendedUsersTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        # High score public user but in a different organization
        other_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[OrganizationFactory().get_users()],
            last_login=timezone.localtime(timezone.now()),
        )
        UserScoreFactory(
            user=other_user,
            completeness=20.0,
            activity=5.0,
            score=25.0,
        )
        UserEmbeddingFactory(
            item=other_user, embedding=[*1024 * [1.0]], is_visible=True
        )
        # High score user public but inactive
        inactive_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now()) - timedelta(days=365),
        )
        UserScoreFactory(
            user=inactive_user,
            completeness=20.0,
            activity=0.09,
            score=20.09,
        )
        UserEmbeddingFactory(
            item=inactive_user, embedding=[*1024 * [1.0]], is_visible=True
        )
        # Public user with highest score
        public_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now()),
        )
        UserScoreFactory(
            user=public_user,
            completeness=20.0,
            activity=5.0,
            score=25.0,
        )
        UserEmbeddingFactory(
            item=public_user, embedding=[*1024 * [0.0]], is_visible=True
        )
        # Public user with second highest score
        public_user_2 = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now()),
        )
        UserScoreFactory(
            user=public_user_2,
            completeness=10.0,
            activity=5.0,
            score=15.0,
        )
        UserEmbeddingFactory(
            item=public_user_2, embedding=[*768 * [0.0], *256 * [1.0]], is_visible=True
        )
        # Private user
        private_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now()),
        )
        UserScoreFactory(
            user=private_user,
            completeness=20.0,
            activity=5.0,
            score=25.0,
        )
        UserEmbeddingFactory(
            item=private_user, embedding=[*512 * [0.0], *512 * [1.0]], is_visible=True
        )
        # Organization user
        org_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now()),
        )
        UserScoreFactory(
            user=org_user,
            completeness=20.0,
            activity=5.0,
            score=25.0,
        )
        UserEmbeddingFactory(
            item=org_user, embedding=[*256 * [0.0], *768 * [1.0]], is_visible=True
        )
        cls.users = {
            "other": other_user,
            "inactive": inactive_user,
            "public": public_user,
            "public_2": public_user_2,
            "private": private_user,
            "org": org_user,
        }
        cls.project = ProjectFactory(organizations=[cls.organization])
        ProjectEmbeddingFactory(
            item=cls.project, embedding=[*1024 * [1.0]], is_visible=True
        )
        cls.project.members.add(public_user)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public", "public_2"]),
            (TestRoles.DEFAULT, ["public_2", "public"]),
            (TestRoles.SUPERADMIN, ["org", "private", "public_2", "public"]),
            (TestRoles.ORG_ADMIN, ["org", "private", "public_2", "public"]),
            (TestRoles.ORG_FACILITATOR, ["org", "private", "public_2", "public"]),
            (TestRoles.ORG_USER, ["org", "public_2", "public"]),
        ]
    )
    def test_user_recommended_users(self, role, retrieved_users):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        if role != TestRoles.ANONYMOUS:
            UserEmbeddingFactory(item=user, embedding=[*1024 * [1.0]], is_visible=True)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "RecommendedUsers-for-user",
                args=(self.organization.code,),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_users))
        if role == TestRoles.ANONYMOUS:
            self.assertSetEqual(
                {user["id"] for user in content},
                {self.users[user].id for user in retrieved_users},
            )
        else:
            self.assertListEqual(
                [user["id"] for user in content],
                [self.users[user].id for user in retrieved_users],
            )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public_2"]),
            (TestRoles.DEFAULT, ["public_2"]),
            (TestRoles.SUPERADMIN, ["org", "private", "public_2"]),
            (TestRoles.ORG_ADMIN, ["org", "private", "public_2"]),
            (TestRoles.ORG_FACILITATOR, ["org", "private", "public_2"]),
            (TestRoles.ORG_USER, ["org", "public_2"]),
        ]
    )
    def test_project_recommended_users(self, role, retrieved_users):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "RecommendedUsers-for-project",
                args=(self.organization.code, self.project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_users))
        self.assertListEqual(
            [user["id"] for user in content],
            [self.users[user].id for user in retrieved_users],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public_2"]),
            (TestRoles.DEFAULT, ["public_2"]),
            (TestRoles.SUPERADMIN, ["org", "private", "public_2"]),
            (TestRoles.ORG_ADMIN, ["org", "private", "public_2"]),
            (TestRoles.ORG_FACILITATOR, ["org", "private", "public_2"]),
            (TestRoles.ORG_USER, ["org", "public_2"]),
        ]
    )
    def test_project_recommended_random_users(self, role, retrieved_users):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "RecommendedUsers-random-for-project",
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
            [self.users[user].id for user in retrieved_users[:2]],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["public_2", "public"]),
            (TestRoles.DEFAULT, ["public_2", "public"]),
            (TestRoles.SUPERADMIN, ["org", "private", "public_2", "public"]),
            (TestRoles.ORG_ADMIN, ["org", "private", "public_2", "public"]),
            (TestRoles.ORG_FACILITATOR, ["org", "private", "public_2", "public"]),
            (TestRoles.ORG_USER, ["org", "public_2", "public"]),
        ]
    )
    def test_user_recommended_random_users(self, role, retrieved_users):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        if role != TestRoles.ANONYMOUS:
            UserEmbeddingFactory(item=user, embedding=[*1024 * [1.0]], is_visible=True)
        response = self.client.get(
            reverse(
                "RecommendedUsers-random-for-user",
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
            [self.users[user].id for user in retrieved_users[:2]],
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
            reverse("RecommendedUsers-for-user", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        embedding.refresh_from_db()
        self.assertListEqual(list(embedding.embedding), vector)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertListEqual(
            [user["id"] for user in content],
            [self.users[user].id for user in ["org", "private", "public_2", "public"]],
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
            reverse("RecommendedUsers-for-user", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        embedding = UserEmbedding.objects.filter(item=user)
        self.assertTrue(embedding.exists())
        self.assertListEqual(list(embedding.get().embedding), vector)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertListEqual(
            [user["id"] for user in content],
            [self.users[user].id for user in ["org", "private", "public_2", "public"]],
        )

    def test_project_recommended_users_multiple_lookups(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(
            reverse(
                "RecommendedUsers-for-project",
                args=(self.organization.code, self.project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertSetEqual(
            {project["id"] for project in content},
            {self.users[user].id for user in ["org", "private", "public_2"]},
        )
        response = self.client.get(
            reverse(
                "RecommendedUsers-for-project",
                args=(self.organization.code, self.project.slug),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertSetEqual(
            {project["id"] for project in content},
            {self.users[user].id for user in ["org", "private", "public_2"]},
        )
