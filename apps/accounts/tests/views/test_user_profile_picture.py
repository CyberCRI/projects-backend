from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class CreateUserProfilePictureTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_user_profile_picture(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(groups=[organization.get_users()])
        user = self.get_test_user(
            role, organization=organization, owned_instance=instance
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


class UpdateUserProfilePictureTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_user_profile_picture(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(
            groups=[organization.get_users()], profile_picture=self.get_test_image()
        )
        instance.profile_picture.owner = instance
        instance.profile_picture.save()
        user = self.get_test_user(
            role, organization=organization, owned_instance=instance
        )
        self.client.force_authenticate(user)
        payload = {
            "scale_x": 2.0,
            "scale_y": 2.0,
            "left": 1.0,
            "top": 1.0,
            "natural_ratio": 1.0,
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


class DeleteUserProfilePictureTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_user_profile_picture(self, role, expected_code):
        organization = OrganizationFactory()
        instance = UserFactory(
            groups=[organization.get_users()], profile_picture=self.get_test_image()
        )
        instance.profile_picture.owner = instance
        instance.profile_picture.save()
        user = self.get_test_user(
            role, organization=organization, owned_instance=instance
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
