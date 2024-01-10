from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.factories import AttachmentFileFactory
from apps.files.models import AttachmentFile, AttachmentType
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class CreateAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_attachment_file(self, role, expected_code):
        project = self.project
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(project.id,)),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["mime"] == payload["mime"]
            assert content["title"] == payload["title"]
            with AttachmentFile.objects.get(id=content["id"]).file as file:
                assert file.read() == b"test attachment file"


class UpdateAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_attachment_file(self, role, expected_code):
        project = self.project
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        attachment_file = AttachmentFileFactory(project=project)
        payload = {"title": faker.text(max_nb_chars=50)}
        response = self.client.patch(
            reverse("AttachmentFile-detail", args=(project.id, attachment_file.id)),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert content["title"] == payload["title"]


class DeleteAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_attachment_file(self, role, expected_code):
        project = self.project
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        attachment_file = AttachmentFileFactory(project=project)
        response = self.client.delete(
            reverse("AttachmentFile-detail", args=(project.id, attachment_file.id)),
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not AttachmentFile.objects.filter(id=attachment_file.id).exists()


class ListAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = {
            "public": ProjectFactory(
                publication_status=Project.PublicationStatus.PUBLIC,
                organizations=[cls.organization],
            ),
            "org": ProjectFactory(
                publication_status=Project.PublicationStatus.ORG,
                organizations=[cls.organization],
            ),
            "private": ProjectFactory(
                publication_status=Project.PublicationStatus.PRIVATE,
                organizations=[cls.organization],
            ),
        }
        cls.attachment_files = {
            "public": AttachmentFileFactory(project=cls.projects["public"]),
            "org": AttachmentFileFactory(project=cls.projects["org"]),
            "private": AttachmentFileFactory(project=cls.projects["private"]),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_attachment_files(self, role, retrieved_attachment_files):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        for publication_status, project in self.projects.items():
            response = self.client.get(
                reverse(
                    "AttachmentFile-list",
                    args=(project.id,),
                ),
            )
            assert response.status_code == status.HTTP_200_OK
            content = response.json()["results"]
            if publication_status in retrieved_attachment_files:
                assert len(content) == 1
                assert content[0]["id"] == self.attachment_files[publication_status].id
            else:
                assert len(content) == 0


class ValidateAttachmentFileTestCase(JwtAPITestCase):
    def test_create_identical_files(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        project = ProjectFactory()
        file_a = SimpleUploadedFile(
            "test_attachment_file.txt",
            b"test attachment file",
            content_type="text/plain",
        )
        file_b = SimpleUploadedFile(
            "test_attachment_file.txt",
            b"test attachment file",
            content_type="text/plain",
        )
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "attachment_type": AttachmentType.FILE,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(project.id,)),
            data={"file": file_a, **payload},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        response = self.client.post(
            reverse("AttachmentFile-list", args=(project.id,)),
            data={"file": file_b, **payload},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["error"] == [
            "The file you are trying to upload is already attached to this project."
        ]
