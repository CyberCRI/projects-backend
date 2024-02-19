from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateOrganizationLogoTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_organization_logo(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse("Organization-logo-list", args=(self.organization.code,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)


class UpdateOrganizationLogoTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.owner = UserFactory()
        cls.image = cls.get_test_image(owner=cls.owner)
        cls.organization = OrganizationFactory(logo_image=cls.image)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_organization_logo(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.image
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
                "Organization-logo-detail",
                args=(self.organization.code, self.image.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            assert response.json()["scale_x"] == payload["scale_x"]
            assert response.json()["scale_y"] == payload["scale_y"]
            assert response.json()["left"] == payload["left"]
            assert response.json()["top"] == payload["top"]
            assert response.json()["natural_ratio"] == payload["natural_ratio"]


class DeleteOrganizationLogoTestCase(JwtAPITestCase):
    def test_delete_organization_logo(self):
        organization = OrganizationFactory()
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Organization-logo-detail",
                args=(organization.code, organization.logo_image.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
