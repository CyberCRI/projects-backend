from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.factories import PeopleGroupImageFactory, get_image_file
from apps.files.models import PeopleGroupImage
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class PeopleGroupImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        cls.group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )

    @parameterized.expand(
        [
            (
                TestRoles.ANONYMOUS,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.DEFAULT,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.SUPERADMIN,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_ADMIN,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_FACILITATOR,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_USER,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_LEADER,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_MANAGER,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_MEMBER,
                PeopleGroup.PublicationStatus.PUBLIC,
                status.HTTP_200_OK,
            ),
            # organization
            (
                TestRoles.ANONYMOUS,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                TestRoles.DEFAULT,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                TestRoles.SUPERADMIN,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_ADMIN,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_FACILITATOR,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_USER,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_LEADER,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_MANAGER,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_MEMBER,
                PeopleGroup.PublicationStatus.ORG,
                status.HTTP_200_OK,
            ),
            # private
            (
                TestRoles.ANONYMOUS,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                TestRoles.DEFAULT,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                TestRoles.SUPERADMIN,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_ADMIN,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_FACILITATOR,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.ORG_USER,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                TestRoles.GROUP_LEADER,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_MANAGER,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_200_OK,
            ),
            (
                TestRoles.GROUP_MEMBER,
                PeopleGroup.PublicationStatus.PRIVATE,
                status.HTTP_200_OK,
            ),
        ]
    )
    def test_peoplegroup_images(self, role, publication_status, role_status_code):
        people_group = PeopleGroupFactory(
            organization=self.organization,
            publication_status=publication_status,
        )
        PeopleGroupImageFactory(people_group=people_group)
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)

        response = self.client.get(
            reverse(
                "PeopleGroupGallery-list",
                args=(self.organization.code, people_group.id),
            ),
        )

        self.assertEqual(response.status_code, role_status_code)
        if role_status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(len(data["results"]), 1)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_404_NOT_FOUND),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND),
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
        payload = {"file": get_image_file()}
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
            (TestRoles.ANONYMOUS, status.HTTP_404_NOT_FOUND),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND),
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
