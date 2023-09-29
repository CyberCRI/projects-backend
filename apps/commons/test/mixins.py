import os
from typing import List, Tuple
from unittest import skipUnless

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class ImageStorageTestCaseMixin:
    def create_org_user(
        self, permissions: List[str]
    ) -> Tuple[Project, ProjectUser, Organization]:
        organization = OrganizationFactory()
        permissions = [(permission, organization) for permission in permissions]
        project = ProjectFactory()
        user = UserFactory(permissions=permissions)
        project.organizations.add(organization)
        self.client.force_authenticate(user)
        return project, user, organization

    def create_project_member(
        self, permissions: List[str]
    ) -> Tuple[Project, ProjectUser]:
        project = ProjectFactory()
        permissions = [(permission, project) for permission in permissions]
        user = UserFactory(permissions=permissions)
        self.client.force_authenticate(user)
        return project, user

    def create_people_group_member(
        self, permissions: List[str]
    ) -> Tuple[PeopleGroup, ProjectUser]:
        people_group = PeopleGroupFactory()
        permissions = [(permission, people_group) for permission in permissions]
        user = UserFactory(permissions=permissions)
        self.client.force_authenticate(user)
        return people_group, user

    def create_user(self, permissions: List[str] = None) -> ProjectUser:
        permissions = permissions or []
        permissions = [(permission, None) for permission in permissions]
        project_user = UserFactory(permissions=permissions)
        self.client.force_authenticate(project_user)
        return project_user

    def assert_get_image(self, view_name, field_name, factory, denied=False, **kwargs):
        image = self.get_test_image()
        getattr(factory, field_name).add(image)
        factory.save()
        response = self.client.get(
            reverse(view_name, kwargs={"pk": image.pk, **kwargs})
        )
        if not denied:
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        else:
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.content
            )

    def assert_image_upload(self, view_name, detail_view=None, denied=False, **kwargs):
        payload = {"file": self.get_test_image_file()}
        url = reverse(view_name, kwargs=kwargs)
        response = self.client.post(url, data=payload, format="multipart")
        if not denied:
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.content
            )
            self.assertIsNotNone(response.json()["static_url"])
            if detail_view:
                response = self.client.get(
                    reverse(detail_view, kwargs={"pk": response.json()["id"], **kwargs})
                )
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        else:
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.content
            )

    def assert_image_too_large(self, view_name, **kwargs):
        payload = {"file": self.get_oversized_test_image_file()}
        url = reverse(view_name, kwargs=kwargs)
        response = self.client.post(url, data=payload, format="multipart")
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def assert_delete_mtm_image(
        self, view_name, field_name, factory, denied=False, **kwargs
    ):
        image = self.get_test_image()
        getattr(factory, field_name).add(image)
        factory.save()
        response = self.client.delete(
            reverse(view_name, kwargs={"pk": image.pk, **kwargs})
        )
        if not denied:
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        else:
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.content
            )

    def assert_delete_fk_image(
        self, view_name, field_name, factory, denied=False, **kwargs
    ):
        image = self.get_test_image()
        setattr(factory, field_name, image)
        factory.save()
        if isinstance(factory, ProjectUser):
            image.owner = factory
            image.save()
        response = self.client.delete(
            reverse(view_name, kwargs={"pk": image.pk, **kwargs})
        )
        if not denied:
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        else:
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.content
            )

    def assert_delete_fk_image_protected(
        self, view_name, field_name, factory, **kwargs
    ):
        image = self.get_test_image()
        setattr(factory, field_name, image)
        factory.save()
        response = self.client.delete(
            reverse(view_name, kwargs={"pk": image.pk, **kwargs})
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


def skipUnlessAlgolia(decorated):  # noqa : N802
    """Skip decorated tests if ennvar `TEST_ALGOLIA` has not been set to 1."""
    check = bool(int(os.getenv("TEST_ALGOLIA", 0)))
    msg = "Algolia test skipped, use envvar 'TEST_ALGOLIA=1' to test"
    return skipUnless(check, msg)(decorated)


def skipUnlessGoogle(decorated):  # noqa : N802
    """Skip decorated tests if ennvar `TEST_ALGOLIA` has not been set to 1."""
    check = bool(int(os.getenv("TEST_GOOGLE", 0)))
    msg = "Google test skipped, use envvar 'TEST_GOOGLE=1' to test"
    return skipUnless(check, msg)(decorated)
