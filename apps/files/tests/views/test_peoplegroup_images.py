import mimetypes

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.models import PeopleGroupImage
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class PeopleGroupImageTestCase(JwtAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.organization = OrganizationFactory()
        self.group = PeopleGroupFactory(organization=self.organization)

    def create_images(self):
        image_data = faker.image((1, 1), image_format="jpeg")
        return SimpleUploadedFile(
            "image.jpg", image_data, content_type=mimetypes.types_map[".jpeg"]
        )

    def test_peoplegroup_images(self):
        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user)

        response = self.client.get(
            reverse(
                "PeopleGroupGallery-list", args=(self.organization.code, self.group.id)
            ),
        )

        data = response.json()
        self.assertListEqual(data["results"], [])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_201_CREATED),
            (TestRoles.GROUP_MANAGER, status.HTTP_201_CREATED),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_peoplegroup_create_images(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.group])
        self.client.force_authenticate(user)
        payload = {"file": self.create_images()}
        url = reverse(
            "PeopleGroupGallery-list", args=(self.organization.code, self.group.id)
        )

        # create images
        response = self.client.post(
            url,
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)

        if expected_code != status.HTTP_201_CREATED:
            return

        # get list images
        response = self.client.get(
            url,
            data=payload,
            format="multipart",
        )
        data = response.json()
        self.assertEqual(len(data["results"]), 1)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_peoplegroup_delete_images(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.group])
        self.client.force_authenticate(user)

        image = PeopleGroupImage.objects.create(
            people_group=self.group, file=self.get_test_image_file()
        )

        url = reverse(
            "PeopleGroupGallery-detail",
            args=(self.organization.code, self.group.id, image.id),
        )

        # create images
        response = self.client.delete(url)
        self.assertEqual(response.status_code, expected_code)
        if expected_code != status.HTTP_204_NO_CONTENT:
            return

        # get list images
        url = reverse(
            "PeopleGroupGallery-list",
            args=(self.organization.code, self.group.id),
        )
        response = self.client.get(url)
        data = response.json()
        self.assertListEqual(data["results"], [])
