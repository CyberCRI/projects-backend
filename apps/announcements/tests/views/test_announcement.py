from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class TestParams:
    list_route = "Announcement-list"
    detail_route = "Announcement-detail"
    factory = AnnouncementFactory

    @staticmethod
    def create_payload(project):
        return {
            "title": "title",
            "description": "description",
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": True,
            "project_id": project.id,
        }

    @staticmethod
    def create_partial_payload():
        return {"description": "new description"}


class AnnouncementTestCaseNoPermission(JwtAPITestCase, TestParams):
    def test_create_no_permission(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_retrieve_public_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
        )

    def test_patch_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_put_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_destroy_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )


class AnnouncementTestCaseBasePermission(JwtAPITestCase, TestParams):
    def test_create_base_permission(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        user = UserFactory(permissions=[("projects.change_project", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", None)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", None)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", None)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        user = UserFactory(permissions=[("projects.view_project", None)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
        )

    def test_patch_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        user = UserFactory(permissions=[("projects.change_project", None)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        user = UserFactory(permissions=[("projects.change_project", None)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.change_project", None)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )


class AnnouncementTestCaseProjectPermission(JwtAPITestCase, TestParams):
    def test_create_project_permission(self):
        project = ProjectFactory()
        user = UserFactory(permissions=[("projects.change_project", project)])
        payload = self.create_payload(project)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(permissions=[("projects.view_project", project)])
        instance = self.factory(project=project)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        user = UserFactory(permissions=[("projects.view_project", project)])
        instance = self.factory(project=project)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        user = UserFactory(permissions=[("projects.view_project", project)])
        instance = self.factory(project=project)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(permissions=[("projects.view_project", project)])
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
        )

    def test_patch_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(permissions=[("projects.change_project", project)])
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(permissions=[("projects.change_project", project)])
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(permissions=[("projects.change_project", project)])
        instance = self.factory(project=project)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )


class AnnouncementTestCaseOrganizationPermission(JwtAPITestCase, TestParams):
    def test_create_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.change_project", organization)])
        project = ProjectFactory()
        project.organizations.add(organization)
        payload = self.create_payload(project)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.view_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        instance = self.factory(project=project)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.view_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project.organizations.add(organization)
        instance = self.factory(project=project)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.view_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        project.organizations.add(organization)
        instance = self.factory(project=project)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.view_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
        )

    def test_patch_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.change_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.change_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organization.change_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        instance = self.factory(project=project)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )
