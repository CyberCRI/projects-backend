from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase, TagTestCaseMixin, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import SkillFactory, TagFactory
from apps.skills.models import Skill

faker = Faker()


class CreateSkillTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag = TagFactory()

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
    def test_create_skill(self, role, expected_code):
        organization = self.organization
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        self.client.force_authenticate(user)
        payload = {
            "tag": self.tag.id,
            "level": faker.pyint(1, 4),
            "level_to_reach": faker.pyint(1, 4),
            "needs_mentor": faker.pybool(),
            "can_mentor": faker.pybool(),
            "comment": faker.text(),
        }
        response = self.client.post(
            reverse("Skill-list", args=(instance.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            self.assertEqual(response.json()["user"], instance.id)
            self.assertEqual(response.json()["tag"]["id"], payload["tag"])
            self.assertEqual(response.json()["level"], payload["level"])
            self.assertEqual(
                response.json()["level_to_reach"], payload["level_to_reach"]
            )
            self.assertEqual(response.json()["needs_mentor"], payload["needs_mentor"])
            self.assertEqual(response.json()["can_mentor"], payload["can_mentor"])
            self.assertEqual(response.json()["comment"], payload["comment"])


class UpdateSkillTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.skill = SkillFactory()
        cls.other_user = UserFactory()

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
            "user": self.other_user.id,  # check if this field is ignored
            "level": faker.pyint(1, 4),
            "level_to_reach": faker.pyint(1, 4),
            "needs_mentor": faker.pybool(),
            "can_mentor": faker.pybool(),
            "comment": faker.text(),
        }
        response = self.client.patch(
            reverse("Skill-detail", args=(self.skill.user.id, self.skill.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["user"], self.skill.user.id)
            self.assertEqual(response.json()["level"], payload["level"])
            self.assertEqual(
                response.json()["level_to_reach"], payload["level_to_reach"]
            )
            self.assertEqual(response.json()["needs_mentor"], payload["needs_mentor"])
            self.assertEqual(response.json()["can_mentor"], payload["can_mentor"])
            self.assertEqual(response.json()["comment"], payload["comment"])


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
        response = self.client.delete(
            reverse("Skill-detail", args=(skill.user.id, skill.id))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Skill.objects.filter(id=skill.id).exists())
