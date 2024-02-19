from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import SkillFactory, UserFactory
from apps.accounts.models import Skill
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.commons.test.testcases import TagTestCaseMixin
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateSkillTestCase(JwtAPITestCase, TagTestCaseMixin):
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
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_create_skill(self, role, expected_code, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        organization = self.organization
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        self.client.force_authenticate(user)
        payload = {
            "user": instance.id,
            "wikipedia_tag": wikipedia_qid,
            "level": faker.pyint(1, 4),
            "level_to_reach": faker.pyint(1, 4),
        }
        response = self.client.post(reverse("Skill-list"), data=payload)
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            self.assertEqual(response.json()["user"], instance.id)
            self.assertEqual(
                response.json()["wikipedia_tag"]["wikipedia_qid"], wikipedia_qid
            )
            self.assertEqual(response.json()["level"], payload["level"])
            self.assertEqual(
                response.json()["level_to_reach"], payload["level_to_reach"]
            )


class UpdateSkillTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.skill = SkillFactory()

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
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.skill
        )
        self.client.force_authenticate(user)
        payload = {
            "level": faker.pyint(1, 4),
        }
        response = self.client.patch(
            reverse("Skill-detail", args=(self.skill.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["level"], payload["level"])


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
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Skill.objects.filter(id=skill.id).exists())
