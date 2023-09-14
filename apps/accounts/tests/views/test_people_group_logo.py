from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase


class UserProfilePictureTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    view = "PeopleGroup-logo-list"
    field_name = "logo_image"
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
        people_group, _ = self.create_people_group_member(
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
