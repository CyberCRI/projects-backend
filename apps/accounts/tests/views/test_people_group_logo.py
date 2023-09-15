from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase


class CreatePeopleGroupHeaderTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.GROUP_LEADER, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.GROUP_MANAGER, status.HTTP_201_CREATED),
            (JwtAPITestCase.Roles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_people_group_logo(self, role, expected_code):
        people_group = PeopleGroupFactory()
        user = self.get_test_user(role, people_group=people_group)
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse(
                "PeopleGroup-logo-list",
                args=(people_group.organization.code, people_group.id),
            ),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert response.json()["static_url"] is not None


class UpdatePeopleGroupHeaderTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.GROUP_LEADER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.GROUP_MANAGER, status.HTTP_200_OK),
            (JwtAPITestCase.Roles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_people_group_logo(self, role, expected_code):
        people_group = PeopleGroupFactory(logo_image=self.get_test_image())
        user = self.get_test_user(role, owned_instance=people_group.logo_image, people_group=people_group)
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
                "PeopleGroup-logo-list",
                args=(people_group.organization.code, people_group.id),
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


class DeletePeopleGroupHeaderTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (JwtAPITestCase.Roles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (JwtAPITestCase.Roles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.OWNER, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (JwtAPITestCase.Roles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (JwtAPITestCase.Roles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_people_group_logo(self, role, expected_code):
        people_group = PeopleGroupFactory(logo_image=self.get_test_image())
        user = self.get_test_user(role, owned_instance=people_group.logo_image, people_group=people_group)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "PeopleGroup-logo-list",
                args=(people_group.organization.code, people_group.id),
            ),
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            people_group.refresh_from_db()
            assert not people_group.logo_image
