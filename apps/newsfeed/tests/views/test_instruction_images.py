from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.newsfeed.factories import InstructionFactory
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateInstructionImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_instruction_image(self, role, expected_code):
        organization = self.organization
        instruction = InstructionFactory(
            organization=self.organization, people_groups=[self.people_group]
        )
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "file": self.get_test_image_file(),
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
            "scale_y": faker.pyfloat(min_value=1.0, max_value=2.0),
            "left": faker.pyfloat(min_value=1.0, max_value=2.0),
            "top": faker.pyfloat(min_value=1.0, max_value=2.0),
            "natural_ratio": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.post(
            reverse(
                "Instruction-images-list",
                args=(organization.code, instruction.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertIsNotNone(content["static_url"])
            self.assertEqual(
                content["static_url"] + "/",
                reverse(
                    "Instruction-images-detail",
                    args=(organization.code, instruction.id, content["id"]),
                ),
            )
            self.assertEqual(content["scale_x"], payload["scale_x"])
            self.assertEqual(content["scale_y"], payload["scale_y"])
            self.assertEqual(content["left"], payload["left"])
            self.assertEqual(content["top"], payload["top"])
            self.assertEqual(content["natural_ratio"], payload["natural_ratio"])


class UpdateInstructionImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.image = cls.get_test_image()
        cls.instruction = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.people_group],
        )
        cls.instruction.images.add(cls.image)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_instruction_image(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
            "scale_y": faker.pyfloat(min_value=1.0, max_value=2.0),
            "left": faker.pyfloat(min_value=1.0, max_value=2.0),
            "top": faker.pyfloat(min_value=1.0, max_value=2.0),
            "natural_ratio": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.patch(
            reverse(
                "Instruction-images-detail",
                args=(self.organization.code, self.instruction.id, self.image.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["scale_x"], payload["scale_x"])
            self.assertEqual(response.json()["scale_y"], payload["scale_y"])
            self.assertEqual(response.json()["left"], payload["left"])
            self.assertEqual(response.json()["top"], payload["top"])
            self.assertEqual(response.json()["natural_ratio"], payload["natural_ratio"])


class DeleteInstructionImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.instruction = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.people_group],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_instruction_image(self, role, expected_code):
        image = self.get_test_image()
        self.instruction.images.add(image)
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Instruction-images-detail",
                args=(self.organization.code, self.instruction.id, image.id),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.instruction.refresh_from_db()
            self.assertFalse(self.instruction.images.filter(id=image.id).exists())


class RetrieveInstructionImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.private_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )
        cls.org_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )

        cls.none_instruction = InstructionFactory(
            organization=cls.organization, visible_by_all=False
        )
        cls.none_image = cls.get_test_image()
        cls.none_instruction.images.add(cls.none_image)

        cls.all_instruction = InstructionFactory(
            organization=cls.organization, visible_by_all=True
        )
        cls.all_image = cls.get_test_image()
        cls.all_instruction.images.add(cls.all_image)

        cls.public_instruction = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.public_people_group],
            visible_by_all=False,
        )
        cls.public_image = cls.get_test_image()
        cls.public_instruction.images.add(cls.public_image)

        cls.private_instruction = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.private_people_group],
            visible_by_all=False,
        )
        cls.private_image = cls.get_test_image()
        cls.private_instruction.images.add(cls.private_image)

        cls.org_instruction = InstructionFactory(
            organization=cls.organization,
            people_groups=[cls.org_people_group],
            visible_by_all=False,
        )
        cls.org_image = cls.get_test_image()
        cls.org_instruction.images.add(cls.org_image)

        cls.instruction = {
            "none": {
                "instruction": cls.none_instruction,
                "image": cls.none_image,
            },
            "all": {
                "instruction": cls.all_instruction,
                "image": cls.all_image,
            },
            "public": {
                "instruction": cls.public_instruction,
                "image": cls.public_image,
            },
            "private": {
                "instruction": cls.private_instruction,
                "image": cls.private_image,
            },
            "org": {
                "instruction": cls.org_instruction,
                "image": cls.org_image,
            },
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("all",)),
            (TestRoles.DEFAULT, ("all",)),
            (TestRoles.SUPERADMIN, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_USER, ("none", "all")),
            (TestRoles.GROUP_LEADER, ("all", "private")),
            (TestRoles.GROUP_MANAGER, ("all", "private")),
            (TestRoles.GROUP_MEMBER, ("all", "private")),
        ]
    )
    def test_retrieve_instruction_images(self, role, retrieved_instructions):
        user = self.get_parameterized_test_user(
            role, instances=[self.private_people_group]
        )
        self.client.force_authenticate(user)
        for key, value in self.instruction.items():
            instruction_id = value["instruction"].id
            image_id = value["image"].id
            response = self.client.get(
                reverse(
                    "Instruction-images-detail",
                    args=(self.organization.code, instruction_id, image_id),
                )
            )
            if key in retrieved_instructions:
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
