from typing import List

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import LocationFactory, ProjectFactory
from apps.projects.models import Location, Project


class TestParams:
    list_route = "Location-list"
    detail_route = "Location-detail"
    factory = LocationFactory

    @staticmethod
    def create_payload(project):
        return {
            "title": "title",
            "description": "description",
            "lat": 0,
            "lng": 0,
            "type": Location.LocationType.TEAM,
            "project_id": project.id,
        }

    @staticmethod
    def create_partial_payload():
        return {"title": "new title", "description": "new description"}


class LocationTestCaseAnonymous(JwtAPITestCase, TestParams):
    def test_create_anonymous(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_retrieve_public_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.json()
        )

    def test_retrieve_org_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.json()
        )

    def test_list_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()]),
        )

    def test_patch_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_put_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_destroy_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )


class LocationTestCaseNoPermission(JwtAPITestCase, TestParams):
    def test_create_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory()
        payload = self.create_payload(project)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_retrieve_public_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.json()
        )

    def test_retrieve_org_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.json()
        )

    def test_list_public_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()]),
        )

    def test_patch_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_put_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_destroy_no_permission(self):
        self.client.force_authenticate(UserFactory())
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )


class LocationTestCaseProjectPermission(JwtAPITestCase, TestParams):
    def create_project_with_user(
        self,
        permissions: List[str],
        publication_status=Project.PublicationStatus.PUBLIC,
    ):
        project = ProjectFactory(publication_status=publication_status)
        user = UserFactory(
            permissions=[(permission, project) for permission in permissions]
        )
        self.client.force_authenticate(user)
        return project

    def test_create_project_permission(self):
        project = self.create_project_with_user(["projects.change_project"])
        payload = self.create_payload(project)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_project_permission(self):
        project = self.create_project_with_user(["projects.view_project"])
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_project_permission(self):
        project = self.create_project_with_user(
            ["projects.view_project"], Project.PublicationStatus.PRIVATE
        )
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_project_permission(self):
        project = self.create_project_with_user(
            ["projects.view_project"], Project.PublicationStatus.ORG
        )
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_project_permission(self):
        project = self.create_project_with_user(["projects.view_project"])
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()]),
        )

    def test_patch_project_permission(self):
        project = self.create_project_with_user(["projects.change_project"])
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_project_permission(self):
        project = self.create_project_with_user(["projects.change_project"])
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_project_permission(self):
        project = self.create_project_with_user(["projects.change_project"])
        instance = self.factory(project=project)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )


class LocationTestCaseOrgPermission(JwtAPITestCase, TestParams):
    def create_project_in_user_org(
        self,
        permissions: List[str],
        publication_status=Project.PublicationStatus.PUBLIC,
    ):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=publication_status)
        project.organizations.add(organization)
        user = UserFactory(
            permissions=[(permission, organization) for permission in permissions]
        )
        self.client.force_authenticate(user)
        return project

    def test_create_org_permission(self):
        project = self.create_project_in_user_org(["organizations.change_project"])
        payload = self.create_payload(project)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_org_permission(self):
        project = self.create_project_in_user_org(["organizations.view_project"])
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_org_permission(self):
        project = self.create_project_in_user_org(
            ["organizations.view_project"],
            Project.PublicationStatus.PRIVATE,
        )
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_org_permission(self):
        project = self.create_project_in_user_org(
            ["organizations.view_org_project"], Project.PublicationStatus.ORG
        )
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_org_permission(self):
        project = self.create_project_in_user_org(["organizations.view_project"])
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()]),
        )

    def test_patch_org_permission(self):
        project = self.create_project_in_user_org(["organizations.change_project"])
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_org_permission(self):
        project = self.create_project_in_user_org(["organizations.change_project"])
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_org_permission(self):
        project = self.create_project_in_user_org(["organizations.change_project"])
        instance = self.factory(project=project)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
