from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.files.factories import AttachmentFileFactory
from apps.files.models import AttachmentFile, AttachmentType
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class AttachmentFileTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(AttachmentFile)

    def test_create_file(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "mime": "text/plain",
            "title": faker.word(),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(self.project.id,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(AttachmentFile.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(AttachmentFile.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_file(self):
        self.client.force_authenticate(self.superadmin)
        file = AttachmentFileFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=file.pk
        ).update(up_to_date=True)

        payload = {
            translated_field: faker.word()
            for translated_field in AttachmentFile.auto_translated_fields
        }
        response = self.client.patch(
            reverse("AttachmentFile-detail", args=(self.project.id, file.pk)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=file.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(AttachmentFile.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(AttachmentFile.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_file(self):
        self.client.force_authenticate(self.superadmin)
        file = AttachmentFileFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=file.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("AttachmentFile-detail", args=(self.project.id, file.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=file.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
