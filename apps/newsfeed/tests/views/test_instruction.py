import datetime
import random

from django.urls import reverse
from apps.newsfeed.factories import InstructionFactory
from apps.newsfeed.models import Instruction
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.misc.models import Language
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateInstructionTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

        leaders_managers = UserFactory.create_batch(2)
        managers = UserFactory.create_batch(2)
        leaders_members = UserFactory.create_batch(2)
        members = UserFactory.create_batch(2)

        cls.people_group.managers.add(*managers, *leaders_managers)
        cls.people_group.members.add(*members, *leaders_members)
        cls.people_group.leaders.add(*leaders_managers, *leaders_members)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_instruction(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "organization": self.organization.code,
            "title": faker.sentence(),
            "content": faker.text(),
            "language": random.choice(Language.values),  # nosec
            "publication_date": datetime.date.today().isoformat(),
            "people_groups_ids": [self.people_group.id],
            "has_to_be_notified": True,
        }
        response = self.client.post(
            reverse("Instruction-list", args=(organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["content"], payload["content"])
            self.assertEqual(content["language"], payload["language"])
            self.assertEqual(content["people_groups"][0]["id"], payload["people_groups_ids"][0])
            self.assertEqual(content["has_to_be_notified"], payload["has_to_be_notified"])


class UpdateInstructionTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.instruction = InstructionFactory(
            organization=cls.organization, people_groups=[cls.people_group]
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_instruction(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "language": "fr",
            "publication_date": datetime.date.today().isoformat(),
            "has_to_be_notified": True,
        }
        response = self.client.patch(
            reverse(
                "Instruction-detail",
                args=(
                    self.organization.code,
                    self.instruction.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["content"], payload["content"])
            self.assertEqual(content["language"], payload["language"])
            self.assertEqual(content["has_to_be_notified"], payload["has_to_be_notified"])


class DeleteInstructionTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_instruction(self, role, expected_code):
        instruction = InstructionFactory(
            organization=self.organization, people_groups=[self.people_group]
        )
        instruction_id = instruction.id
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Instruction-detail",
                args=(
                    self.organization.code,
                    instruction.id,
                ),
            )
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Instruction.objects.filter(id=instruction_id).exists())


class ValidatePeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.other_organization = OrganizationFactory()
        cls.other_org_people_group = PeopleGroupFactory(
            organization=cls.other_organization
        )

    def setUp(self):
        super().setUp()

    def test_create_instruction_with_people_group_in_other_organization(self):
        user = self.get_parameterized_test_user("superadmin", instances=[])
        self.client.force_authenticate(user=user)
        payload = {
            "organization": self.organization.code,
            "title": faker.sentence(),
            "content": faker.text(),
            "language": "fr",
            "publication_date": datetime.date.today().isoformat(),
            "people_groups_ids": [self.other_org_people_group.id],
            "has_to_be_notified": True,
        }
        response = self.client.post(
            reverse("Instruction-list", args=(self.organization.code,)), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "people_groups_ids": [
                    "The people groups of an instruction must belong to the same organization"
                ]
            },
        )

    def test_update_instruction_with_people_group_in_other_organization(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        instruction = InstructionFactory(organization=self.organization, people_groups=[people_group])
        user = self.get_parameterized_test_user("superadmin", instances=[])
        self.client.force_authenticate(user=user)
        payload = {
            "people_groups_ids": [self.other_org_people_group.id],
        }
        response = self.client.patch(
            reverse(
                "Instruction-detail",
                args=(
                    self.organization.code,
                    instruction.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "people_groups_ids": [
                    "The people groups of an instruction must belong to the same organization"
                ]
            },
        )