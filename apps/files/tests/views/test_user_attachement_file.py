from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.models import AttachmentType, ProjectUserAttachmentFile

faker = Faker()


class CreateProjectUserAttachmentFileTestCase(JwtAPITestCase):
    def test_create_attachment_file(self):
        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
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
        }
        response = self.client.post(
            reverse("ProjectUserAttachmentFile-list", args=(user.id,)),
            data=payload,
            format="multipart",
        )
        content = response.json()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(content["mime"], payload["mime"])
        self.assertEqual(content["title"], payload["title"])
        with ProjectUserAttachmentFile.objects.get(id=content["id"]).file as file:
            self.assertEqual(file.read(), b"test attachment file")

    def test_create_attachment_file_different_user(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user_1)

        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
        }
        response = self.client.post(
            # we try to add attachement on user_2 with user_1 connected
            reverse("ProjectUserAttachmentFile-list", args=(user_2.id,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UpdateProjectUserAttachmentFileTestCase(JwtAPITestCase):
    def test_update_attachment_file(self):
        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user)

        file = ProjectUserAttachmentFile.objects.create(title="title", owner=user)

        payload = {"title": "test"}
        response = self.client.patch(
            reverse("ProjectUserAttachmentFile-detail", args=(user.id, file.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["title"], payload["title"])

    def test_update_attachment_file_different_user(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user_1)

        file = ProjectUserAttachmentFile.objects.create(title="title", owner=user_1)

        payload = {"title": "test"}
        response = self.client.patch(
            # we try to add attachement on user_2 with user_1 connected
            reverse("ProjectUserAttachmentFile-detail", args=(user_2.id, file.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeleteProjectUserAttachmentFileTestCase(JwtAPITestCase):
    def test_delete_attachment_file(self):
        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user)

        file = ProjectUserAttachmentFile.objects.create(title="title", owner=user)

        response = self.client.delete(
            reverse("ProjectUserAttachmentFile-detail", args=(user.id, file.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectUserAttachmentFile.objects.filter(id=file.id).exists())

    def test_delete_attachment_file_different_user(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user_1)

        file = ProjectUserAttachmentFile.objects.create(title="title", owner=user_1)

        response = self.client.delete(
            # we try to add attachement on user_2 with user_1 connected
            reverse("ProjectUserAttachmentFile-detail", args=(user_2.id, file.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GetProjectUserAttachmentFileTestCase(JwtAPITestCase):
    def test_get_attachment_file_from_annonymous(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)

        user_1_file = ProjectUserAttachmentFile.objects.create(
            title="user_1", owner=user_1
        )

        response = self.client.get(
            reverse("ProjectUserAttachmentFile-list", args=(user_1.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        file_ids = [obj["id"] for obj in data["results"]]
        self.assertEqual(file_ids, [user_1_file.id])

    def test_get_attachment_file_from_user(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)

        ProjectUserAttachmentFile.objects.create(title="user_1", owner=user_1)
        user_2_file = ProjectUserAttachmentFile.objects.create(
            title="user_2", owner=user_2
        )

        self.client.force_authenticate(user_1)

        response = self.client.get(
            reverse("ProjectUserAttachmentFile-list", args=(user_2.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        file_ids = [obj["id"] for obj in data["results"]]
        self.assertEqual(file_ids, [user_2_file.id])
