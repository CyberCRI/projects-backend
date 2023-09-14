from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase, UserRoles


class CreatePeopleGroupHeaderTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    @parameterized.expand(
        [
            (UserRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (UserRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (UserRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (UserRoles.ORGANIZATION_ADMIN, status.HTTP_201_CREATED),
            (UserRoles.ORGANIZATION_FACILITATOR, status.HTTP_201_CREATED),
            (UserRoles.ORGANIZATION_USER, status.HTTP_403_FORBIDDEN),
            (UserRoles.PEOPLE_GROUP_LEADER, status.HTTP_201_CREATED),
            (UserRoles.PEOPLE_GROUP_MANAGER, status.HTTP_201_CREATED),
            (UserRoles.PEOPLE_GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_people_group_header(self, role, expected_code):
        instance = PeopleGroupFactory()
        user = self.get_test_user(role, instance)
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse(
                "PeopleGroup-header-list",
                args=(instance.organization.code, instance.id),
            ),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert response.json()["static_url"] is not None


class PeopleGroupHeaderTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    view = "PeopleGroup-header-list"
    field_name = "header_image"
    base_permissions = ["accounts.change_peoplegroup"]
    org_permissions = ["organizations.change_peoplegroup"]
    people_group_permissions = ["accounts.change_peoplegroup"]

    def assert_delete_fk_image(
        self, view_name, field_name, factory, denied=False, **kwargs
    ):
        image = self.get_test_image()
        setattr(factory, field_name, image)
        factory.save()
        response = self.client.delete(reverse(view_name, kwargs=kwargs))
        if not denied:
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        else:
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.content
            )

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        self.create_user(self.base_permissions)
        people_group = PeopleGroupFactory()
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_image_upload(self.view, **kwargs)

    def test_upload_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        people_group = PeopleGroupFactory(organization=organization)
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_image_upload(self.view, **kwargs)

    def test_upload_images_people_group_permission(self):
        people_group, _ = self.create_people_group_member(
            permissions=self.people_group_permissions
        )
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_image_upload(self.view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        self.create_user(self.base_permissions)
        people_group = PeopleGroupFactory()
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_image_too_large(self.view, **kwargs)

    def test_upload_images_no_permission(self):
        self.create_user()
        people_group = PeopleGroupFactory()
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_image_upload(self.view, **kwargs, denied=True)

    # Tests for DELETE calls that should pass
    def test_delete_fk_images_base_permission(self):
        self.create_user(self.base_permissions)
        people_group = PeopleGroupFactory()
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_delete_fk_image(self.view, self.field_name, people_group, **kwargs)

    def test_delete_fk_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        people_group = PeopleGroupFactory(organization=organization)
        kwargs = {
            "organization_code": organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_delete_fk_image(self.view, self.field_name, people_group, **kwargs)

    def test_delete_images_people_group_permission(self):
        people_group, user = self.create_people_group_member(
            permissions=self.people_group_permissions
        )
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_delete_fk_image(self.view, self.field_name, people_group, **kwargs)

    # Tests for DELETE calls that should fail
    def test_delete_fk_images_no_permission(self):
        self.create_user()
        people_group = PeopleGroupFactory()
        kwargs = {
            "organization_code": people_group.organization.code,
            "people_group_id": people_group.id,
        }
        self.assert_delete_fk_image(
            self.view, self.field_name, people_group, denied=True, **kwargs
        )
