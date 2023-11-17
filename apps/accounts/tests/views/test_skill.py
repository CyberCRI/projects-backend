from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import Skill
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.commons.test.testcases import TagTestCase
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateSkillTestCase(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_201_CREATED),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_skill(self, role, expected_code, mocked):
        mocked.side_effect = self.side_effect
        organization = self.organization
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        self.client.force_authenticate(user)
        payload = {
            "user": instance.keycloak_id,
            "wikipedia_tag": "Q1735684",
            "level": 1,
            "level_to_reach": 2,
        }
        response = self.client.post(reverse("Skill-list"), data=payload)
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert response.json()["user"] == instance.keycloak_id
            assert response.json()["wikipedia_tag"]["wikipedia_qid"] == "Q1735684"
            assert response.json()["level"] == 1
            assert response.json()["level_to_reach"] == 2


class UpdateSkillTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_skill(self, role, expected_code):
        organization = self.organization
        skill = SkillFactory(level=1)
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=skill
        )
        self.client.force_authenticate(user)
        payload = {
            "level": 2,
        }
        response = self.client.patch(
            reverse("Skill-detail", args=(skill.id,)), data=payload
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert response.json()["level"] == 2


class DeleteSkillTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_skill(self, role, expected_code):
        organization = self.organization
        skill = SkillFactory()
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=skill
        )
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Skill-detail", args=(skill.id,)))
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not Skill.objects.filter(id=skill.id).exists()
