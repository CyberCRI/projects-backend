from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.models import Image
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import (
    ProjectFactory,
    ProjectTabFactory,
    ProjectTabItemFactory,
)
from apps.projects.models import Project

faker = Faker()


class RetrieveProjectTabItemImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
        }
        cls.tabs = {
            "public": ProjectTabFactory(project=cls.public_project),
            "org": ProjectTabFactory(project=cls.org_project),
            "private": ProjectTabFactory(project=cls.private_project),
        }
        cls.items = {
            "public": ProjectTabItemFactory(tab=cls.tabs["public"]),
            "org": ProjectTabItemFactory(tab=cls.tabs["org"]),
            "private": ProjectTabItemFactory(tab=cls.tabs["private"]),
        }
        owner = UserFactory()
        for item in cls.items.values():
            image = cls.get_test_image(owner=owner)
            item.images.add(image)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_retrieve_tab_item_image(self, role, retrieved_images):
        for publication_status, item in self.items.items():
            image = item.images.first()
            user = self.get_parameterized_test_user(
                role, instances=[item.tab.project], owned_instance=image
            )
            self.client.force_authenticate(user)
            response = self.client.get(
                reverse(
                    "ProjectTabItem-images-detail",
                    args=(item.tab.project.id, item.tab.id, image.id),
                )
            )
            if publication_status in retrieved_images:
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CreateProjectTabItemImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.tab = ProjectTabFactory(project=cls.project)
        cls.item = ProjectTabItemFactory(tab=cls.tab)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_tab_item_image(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
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
            reverse("ProjectTabItem-images-list", args=(self.project.id, self.tab.id)),
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
                    "ProjectTabItem-images-detail",
                    args=(self.project.id, self.tab.id, content["id"]),
                ),
            )
            self.assertEqual(content["scale_x"], payload["scale_x"])
            self.assertEqual(content["scale_y"], payload["scale_y"])
            self.assertEqual(content["left"], payload["left"])
            self.assertEqual(content["top"], payload["top"])
            self.assertEqual(content["natural_ratio"], payload["natural_ratio"])

    def test_tab_item_image_with_relation(self):
        user = self.get_parameterized_test_user(TestRoles.SUPERADMIN)
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
            reverse("ProjectTabItem-images-list", args=(self.project.id, self.tab.id))
            + f"?tab_item_id={self.item.id}",
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertIsNotNone(content["static_url"])
        self.assertEqual(
            content["static_url"] + "/",
            reverse(
                "ProjectTabItem-images-detail",
                args=(self.project.id, self.tab.id, content["id"]),
            ),
        )
        self.item.refresh_from_db()
        self.assertIn(content["id"], self.item.images.values_list("id", flat=True))
        self.assertEqual(content["scale_x"], payload["scale_x"])
        self.assertEqual(content["scale_y"], payload["scale_y"])
        self.assertEqual(content["left"], payload["left"])
        self.assertEqual(content["top"], payload["top"])
        self.assertEqual(content["natural_ratio"], payload["natural_ratio"])


class UpdateProjectTabItemImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.tab = ProjectTabFactory(project=cls.project)
        cls.item = ProjectTabItemFactory(tab=cls.tab)
        cls.owner = UserFactory()
        cls.image = cls.get_test_image(owner=cls.owner)
        cls.item.images.add(cls.image)

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
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_tab_item_image(self, role, expected_code):
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
                "ProjectTabItem-images-detail",
                args=(self.project.id, self.tab.id, self.image.id),
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


class DeleteProjectTabItemImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.tab = ProjectTabFactory(project=cls.project)
        cls.item = ProjectTabItemFactory(tab=cls.tab)
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
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_tab_item_image(self, role, expected_code):
        image = self.get_test_image(owner=self.owner)
        self.item.images.add(image)
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=image
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "ProjectTabItem-images-detail",
                args=(self.project.id, self.tab.id, image.id),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Image.objects.filter(id=image.id).exists())
