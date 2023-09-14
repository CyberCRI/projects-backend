from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.files.factories import AttachmentLinkFactory
from apps.files.tests.views.mock_response import MockResponse
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class AttachmentLinkJwtAPITestCase(JwtAPITestCase):
    list_route = "AttachmentLink-list"
    detail_route = "AttachmentLink-detail"
    factory = AttachmentLinkFactory

    @staticmethod
    def create_partial_payload():
        return {"site_name": "site name"}

    @staticmethod
    def create_payload(project):
        return {
            "site_url": "google.com",
            "project_id": project.id,
        }

    def assert_url_processing_correct(self, response):
        content = response.json()
        mocked_response = MockResponse()
        self.assertEqual(content["attachment_type"], "link", content)
        self.assertEqual(content["site_url"], "https://google.com", content)
        self.assertEqual(content["preview_image_url"], mocked_response.image, content)
        self.assertEqual(content["site_name"], mocked_response.site_name, content)


class AttachmentLinkTestCaseNoPermission(AttachmentLinkJwtAPITestCase):
    def test_create_no_permission(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        url = reverse(self.list_route, kwargs={"project_id": project.id})
        self.client.force_authenticate(UserFactory())
        response = self.client.post(url, data=payload, format="multipart")
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
        assert response.data["title"] == instance.title
        assert response.data["description"] == instance.description

    def test_retrieve_private_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
        )

    def test_retrieve_org_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
        )

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
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
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
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
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
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )


class AttachmentLinkTestCaseBasePermission(AttachmentLinkJwtAPITestCase):
    def test_create_base_permission(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        url = reverse(self.list_route, kwargs={"project_id": project.id})
        user = UserFactory(permissions=[("projects.change_project", None)])
        self.client.force_authenticate(user)
        response = self.client.post(url, data=payload, format="multipart")
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
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
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
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
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


class AttachmentLinkTestCaseProjectPermission(AttachmentLinkJwtAPITestCase):
    def test_create_project_permission(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        url = reverse(self.list_route, kwargs={"project_id": project.id})
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.post(url, data=payload, format="multipart")
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", project)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())

    def test_retrieve_private_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", project)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())

    def test_retrieve_org_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.view_project", project)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())

    def test_list_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        user = UserFactory(permissions=[("projects.view_project", project)])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(self.list_route, kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            sorted([instance1.id, instance2.id]),
            sorted([i["id"] for i in response.json()["results"]]),
        )

    def test_patch_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        kwargs = {"project_id": project.id, "id": instance.id}
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )


class AttachmentLinkTestCaseOrgPermission(AttachmentLinkJwtAPITestCase):
    def test_create_org_permission(self):
        project = ProjectFactory()
        payload = self.create_payload(project)
        url = reverse(self.list_route, kwargs={"project_id": project.id})
        organization = OrganizationFactory()
        organization.projects.add(project)
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(url, data=payload, format="multipart")
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_retrieve_public_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        organization = OrganizationFactory()
        organization.projects.add(project)
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

    def test_retrieve_private_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        user = UserFactory()
        organization = OrganizationFactory()
        organization.projects.add(project)
        user = UserFactory(
            permissions=[("organizations.view_org_project", organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
        )

    def test_retrieve_org_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        organization = OrganizationFactory()
        organization.projects.add(project)
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
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance1 = self.factory(project=project)
        instance2 = self.factory(project=project)
        self.factory()
        organization = OrganizationFactory()
        organization.projects.add(project)
        user = UserFactory(
            permissions=[("organizations.view_org_project", organization)]
        )
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
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        organization = OrganizationFactory()
        organization.projects.add(project)
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_put_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_payload(project)
        kwargs = {"project_id": project.id, "id": instance.id}
        organization = OrganizationFactory()
        organization.projects.add(project)
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        organization = OrganizationFactory()
        organization.projects.add(project)
        user = UserFactory(permissions=[("organizations.change_project", organization)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                self.detail_route, kwargs={"project_id": project.id, "id": instance.id}
            )
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )


class AttachmentLinkTestCaseDuplicate(AttachmentLinkJwtAPITestCase):
    def test_create_duplicate_domain(self):
        link = AttachmentLinkFactory(site_url="https://google.com")
        payload = {"site_url": "https://google.com", "project_id": link.project.id}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": link.project.id}),
            data=payload,
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["This url is already attached to this project."]},
        )

    @patch(target="requests.get", return_value=MockResponse())
    def test_create_duplicate_www_domain(self, mocked):
        link = AttachmentLinkFactory(site_url="https://google.com")
        payload = {"site_url": "https://www.google.com", "project_id": link.project.id}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": link.project.id}),
            data=payload,
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_create_duplicate_https_domain(self):
        link = AttachmentLinkFactory(site_url="https://google.com")
        payload = {"site_url": "https://google.com", "project_id": link.project.id}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": link.project.id}),
            data=payload,
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["This url is already attached to this project."]},
        )

    def test_patch_duplicate_link(self):
        link = AttachmentLinkFactory(site_url="https://google.com")
        link2 = AttachmentLinkFactory(
            site_url="https://other_google.com", project=link.project
        )
        payload = {"site_url": "https://google.com", "project_id": link.project.id}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        kwargs = {"project_id": link.project.id, "id": link2.id}
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["This url is already attached to this project."]},
        )

    def test_put_duplicate_link(self):
        link = AttachmentLinkFactory(site_url="https://google.com")
        link2 = AttachmentLinkFactory(
            site_url="https://other_google.com", project=link.project
        )
        payload = {"site_url": "https://google.com", "project_id": link.project.id}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        kwargs = {"project_id": link.project.id, "id": link2.id}
        response = self.client.put(
            reverse(self.detail_route, kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["This url is already attached to this project."]},
        )

    @patch(target="requests.get", return_value=MockResponse())
    def test_create_duplicate_other_project(self, mocked):
        link = AttachmentLinkFactory(site_url="https://google.com")
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        project = ProjectFactory()
        payload = {"site_url": "https://google.com", "project_id": project.id}
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": link.project.id}),
            data=payload,
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
