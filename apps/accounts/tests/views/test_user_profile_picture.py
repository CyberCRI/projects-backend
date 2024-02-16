from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateUserProfilePictureTestCase(JwtAPITestCase):
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
    def test_create_user_profile_picture(self, role, expected_code):
        organization = self.organization
        instance = UserFactory(groups=[self.organization.get_users()])
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse(
                "UserProfilePicture-list",
                args=(instance.keycloak_id,),
            ),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert response.json()["static_url"] is not None


class UpdateUserProfilePictureTestCase(JwtAPITestCase):
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
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_user_profile_picture(self, role, expected_code):
        organization = self.organization
        instance = UserFactory(
            groups=[organization.get_users()], profile_picture=self.get_test_image()
        )
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
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
                "UserProfilePicture-detail",
                args=(instance.keycloak_id, instance.profile_picture.id),
            ),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert response.json()["scale_x"] == payload["scale_x"]
            assert response.json()["scale_y"] == payload["scale_y"]
            assert response.json()["left"] == payload["left"]
            assert response.json()["top"] == payload["top"]
            assert response.json()["natural_ratio"] == payload["natural_ratio"]


class DeleteUserProfilePictureTestCase(JwtAPITestCase):
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
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_user_profile_picture(self, role, expected_code):
        organization = self.organization
        instance = UserFactory(
            groups=[self.organization.get_users()],
            profile_picture=self.get_test_image(),
        )
        user = self.get_parameterized_test_user(
            role, instances=[organization], owned_instance=instance
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "UserProfilePicture-detail",
                args=(instance.keycloak_id, instance.profile_picture.id),
            ),
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            instance.refresh_from_db()
            assert not instance.profile_picture
