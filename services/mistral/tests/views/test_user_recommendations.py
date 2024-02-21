from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from services.mistral.factories import UserEmbeddingFactory

faker = Faker()


class UserRecommendationTestCase(JwtAPITestCase):
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
