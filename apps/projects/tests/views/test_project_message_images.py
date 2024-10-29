from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.models import Image
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectMessageFactory
from apps.projects.models import Project

faker = Faker()


class RetrieveProjectMessageImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.owner = UserFactory()
        cls.project_message = ProjectMessageFactory(project=cls.project)
        cls.image = cls.get_test_image(owner=cls.owner)
        cls.project_message.images.add(cls.image)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_302_FOUND),
            (TestRoles.OWNER, status.HTTP_302_FOUND),
            (TestRoles.ORG_ADMIN, status.HTTP_302_FOUND),
            (TestRoles.ORG_FACILITATOR, status.HTTP_302_FOUND),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_302_FOUND),
            (TestRoles.PROJECT_OWNER, status.HTTP_302_FOUND),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_302_FOUND),
        ]
    )
    def test_retrieve_project_message_image(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=self.image
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "ProjectMessage-images-detail", args=(self.project.id, self.image.id)
            ),
        )
        self.assertEqual(response.status_code, expected_code)


class CreateProjectMessageImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_project_message_image(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse("ProjectMessage-images-list", args=(self.project.id,)),
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
                    "ProjectMessage-images-detail",
                    args=(self.project.id, content["id"]),
                ),
            )


class UpdateProjectMessageImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.project_message = ProjectMessageFactory(project=cls.project)
        cls.owner = UserFactory()
        cls.image = cls.get_test_image(owner=cls.owner)
        cls.project_message.images.add(cls.image)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_project_message_image(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=self.image
        )
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
                "ProjectMessage-images-detail",
                args=(self.project.id, self.image.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["scale_x"], payload["scale_x"])
            self.assertEqual(content["scale_y"], payload["scale_y"])
            self.assertEqual(content["left"], payload["left"])
            self.assertEqual(content["top"], payload["top"])
            self.assertEqual(content["natural_ratio"], payload["natural_ratio"])


class DeleteProjectMessageImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.project_message = ProjectMessageFactory(project=cls.project)
        cls.owner = UserFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_project_message_image(self, role, expected_code):
        image = self.get_test_image(owner=self.owner)
        self.project_message.images.add(image)
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=image
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "ProjectMessage-images-detail",
                args=(self.project.id, image.id),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Image.objects.filter(id=image.id).exists())


class MiscProjectMessageImageTestCase(JwtAPITestCase):
    def test_multiple_lookups(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        project_message = ProjectMessageFactory()
        image = self.get_test_image()
        project_message.images.add(image)
        response = self.client.get(
            reverse(
                "ProjectMessage-images-detail",
                args=(project_message.project.id, image.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        response = self.client.get(
            reverse(
                "ProjectMessage-images-detail",
                args=(project_message.project.slug, image.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
