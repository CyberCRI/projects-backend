import hashlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from factory.django import FileField
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.files.factories import AttachmentFileFactory
from apps.files.models import AttachmentFile, AttachmentType
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class AttachmentFileJwtAPITestCase(JwtAPITestCase):
    list_route = "AttachmentFile-list"
    detail_route = "AttachmentFile-detail"
    factory = AttachmentFileFactory

    @staticmethod
    def create_partial_payload():
        return {"title": "new title"}

    @staticmethod
    def create_payload(project, file_size=20):
        repetitions = int(file_size / 20)
        return {
            "mime": "mime",
            "title": "title",
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                repetitions * b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
            "project_id": project.id,
        }

    def assert_file_equal(self, response, payload):
        content = response.json()
        self.assertEqual(content["mime"], payload["mime"], content)
        self.assertEqual(content["title"], payload["title"], content)
        with AttachmentFile.objects.get(id=content["id"]).file as file:
            self.assertEqual(file.read(), b"test attachment file")


class AttachmentFileTestCaseNoPermission(AttachmentFileJwtAPITestCase):
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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

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
        instance1 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content a"),
            hashcode=hashlib.sha256(b"content a").hexdigest(),
        )
        instance2 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content b"),
            hashcode=hashlib.sha256(b"content b").hexdigest(),
        )
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
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )


class AttachmentFileTestCaseBasePermission(AttachmentFileJwtAPITestCase):
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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

    def test_list_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance1 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content a"),
            hashcode=hashlib.sha256(b"content a").hexdigest(),
        )
        instance2 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content b"),
            hashcode=hashlib.sha256(b"content b").hexdigest(),
        )
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


class AttachmentFileTestCaseProjectPermission(AttachmentFileJwtAPITestCase):
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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

    def test_list_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance1 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content a"),
            hashcode=hashlib.sha256(b"content a").hexdigest(),
        )
        instance2 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content b"),
            hashcode=hashlib.sha256(b"content b").hexdigest(),
        )
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
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        payload = self.create_partial_payload()
        kwargs = {"project_id": project.id, "id": instance.id}
        user = UserFactory(permissions=[("projects.change_project", project)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
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
            reverse(self.detail_route, kwargs=kwargs), data=payload, format="multipart"
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


class AttachmentFileTestCaseOrgPermission(AttachmentFileJwtAPITestCase):
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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

    def test_retrieve_private_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
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
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)

    def test_list_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance1 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content a"),
            hashcode=hashlib.sha256(b"content a").hexdigest(),
        )
        instance2 = self.factory(
            project=project,
            file=FileField(filename="file.txt", data=b"content b"),
            hashcode=hashlib.sha256(b"content b").hexdigest(),
        )
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


class IdenticalFilesTestCase(AttachmentFileJwtAPITestCase):
    def test_create(self):
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        project = ProjectFactory()
        payload = self.create_payload(project)
        payload2 = self.create_payload(project)
        response = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}),
            data=payload,
            format="multipart",
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        self.assert_file_equal(response, payload)

        response2 = self.client.post(
            reverse(self.list_route, kwargs={"project_id": project.id}),
            data=payload2,
            format="multipart",
        )
        self.assertEqual(
            response2.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
