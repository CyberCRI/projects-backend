from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import (
    CategoryFollowFactory,
    OrganizationFactory,
    ProjectCategoryFactory,
)
from apps.organizations.models import CategoryFollow


class CreateCategoryFollowTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.user = UserFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_201_CREATED),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
        ]
    )
    def test_create_category_follow(self, role, expected_code):
        user = self.get_parameterized_test_user(role, owned_instance=self.user)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("CategoryFollow-list", args=(self.user.id,)),
            data={"category_id": self.category.id},
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["category"]["id"], self.category.id)
            follow = CategoryFollow.objects.get(id=content["category"]["id"])
            self.assertEqual(follow.follower.id, self.user.id)


class DestroyCategoryFollowTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_destroy_category_follow(self, role, expected_code):
        follow = CategoryFollowFactory(category=self.category)
        user = self.get_parameterized_test_user(role, owned_instance=follow)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("CategoryFollow-detail", args=(follow.follower.id, follow.id))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(CategoryFollow.objects.filter(id=follow.id).exists())


class ListCategoryFollowTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.public_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
        )
        cls.org_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
            groups=[cls.organization.get_users()],
        )
        cls.private_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
            groups=[cls.organization.get_users()],
        )
        cls.users = {
            "public": cls.public_user,
            "org": cls.org_user,
            "private": cls.private_user,
        }
        cls.category_follows = {
            key: CategoryFollowFactory(category=cls.category, follower=cls.users[key])
            for key in cls.users.keys()
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
        ]
    )
    def test_list_category_follows(self, role, retrieved_follows):
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.private_user
        )
        self.client.force_authenticate(user)
        for publication_status, user in self.users.items():
            response = self.client.get(reverse("CategoryFollow-list", args=(user.id,)))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            if publication_status in retrieved_follows:
                self.assertEqual(len(content), 1)
                self.assertEqual(
                    content[0]["id"], self.category_follows[publication_status].id
                )
            else:
                self.assertEqual(len(content), 0)
