from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from apps.projects.models import Project


class TestParams:
    list_route = "BlogEntry-list"
    detail_route = "BlogEntry-detail"
    factory = BlogEntryFactory

    @staticmethod
    def create_payload(project):
        return {"title": "title", "content": "content", "project_id": project.id}

    @staticmethod
    def create_partial_payload():
        return {"content": "content"}


class BlogEntryTestCaseAnonymous(JwtAPITestCase, TestParams):
    def test_create_anonymous(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        response = self.client.post(
            reverse(self.list_route, args=[project.id]), data=payload
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
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
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
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
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
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
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


class BlogEntryTestCaseNoPermission(JwtAPITestCase, TestParams):
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
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
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
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
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
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
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


class BlogEntryTestCaseProjectPermission(JwtAPITestCase, TestParams):
    def create_project_in_user_org(
        self, publication_status=Project.PublicationStatus.PUBLIC
    ):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=publication_status)
        project.organizations.add(organization)
        return organization, project

    def test_create_project_permission(self):
        _, project = self.create_project_in_user_org(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        payload = self.create_payload(project)
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        payload["content"] = self.get_base64_image()
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_retrieve_project_permission(self):
        _, project = self.create_project_in_user_org(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", project)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_project_permission(self):
        _, project = self.create_project_in_user_org(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        user = UserFactory(permissions=[("projects.view_project", project)])
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
        _, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_put_project_permission(self):
        _, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_destroy_project_permission(self):
        _, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class BlogEntryTestCaseOrganizationPermission(JwtAPITestCase, TestParams):
    def create_project_in_user_org(
        self, publication_status=Project.PublicationStatus.PUBLIC
    ):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=publication_status)
        project.organizations.add(organization)
        return organization, project

    def test_create_org_permission(self):
        organization, project = self.create_project_in_user_org()
        payload = self.create_payload(project)
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        payload["content"] = self.get_base64_image()
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_retrieve_public_org_permission(self):
        organization, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        organization = project.organizations.first()
        user = UserFactory(permissions=[("organizations.view_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_private_org_permission(self):
        organization, project = self.create_project_in_user_org(
            Project.PublicationStatus.PRIVATE
        )
        instance = self.factory(project=project)
        organization = project.organizations.first()
        user = UserFactory(permissions=[("organizations.view_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_retrieve_org_org_permission(self):
        organization, project = self.create_project_in_user_org(
            Project.PublicationStatus.ORG
        )
        instance = self.factory(project=project)
        organization = project.organizations.first()
        user = UserFactory(
            permissions=[("organizations.view_org_project", organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_org_permission(self):
        organization, project = self.create_project_in_user_org()
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        organization = project.organizations.first()
        user = UserFactory(permissions=[("organizations.view_project", organization)])
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
        organization, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        organization = project.organizations.first()
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_put_org_permission(self):
        organization, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        organization = project.organizations.first()
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_destroy_org_permission(self):
        organization, project = self.create_project_in_user_org()
        instance = self.factory(project=project)
        organization = project.organizations.first()
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
