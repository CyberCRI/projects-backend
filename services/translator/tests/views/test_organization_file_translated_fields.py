from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.files.factories import OrganizationAttachmentFileFactory
from apps.files.models import AttachmentType, OrganizationAttachmentFile
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class OrganizationFileTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(OrganizationAttachmentFile)

    def test_create_organization_file(self):
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
        }
        response = self.client.post(
            reverse("OrganizationAttachmentFile-list", args=(self.organization.code,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(OrganizationAttachmentFile.auto_translated_fields),
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(OrganizationAttachmentFile.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_organization_file(self):
        self.client.force_authenticate(self.superadmin)
        organization_file = OrganizationAttachmentFileFactory(
            organization=self.organization
        )
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization_file.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            OrganizationAttachmentFile.auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, organization_file.pk),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization_file.pk
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(OrganizationAttachmentFile.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in OrganizationAttachmentFile.auto_translated_fields
        }
        response = self.client.patch(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, organization_file.pk),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization_file.pk
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(OrganizationAttachmentFile.auto_translated_fields),
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(OrganizationAttachmentFile.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_organization_file(self):
        self.client.force_authenticate(self.superadmin)
        organization_file = OrganizationAttachmentFileFactory(
            organization=self.organization
        )
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization_file.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, organization_file.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization_file.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
