from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.files.factories import AttachmentLinkFactory
from apps.files.models import AttachmentLink
from apps.files.tests.views.mock_response import MockResponse
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class AttachmentLinkTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(AttachmentLink)

    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_create_link(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response

        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "site_url": faker.url(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("AttachmentLink-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(AttachmentLink.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(AttachmentLink.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_link(self):
        self.client.force_authenticate(self.superadmin)
        link = AttachmentLinkFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=link.pk
        ).update(up_to_date=True)

        payload = {
            translated_field: faker.word()
            for translated_field in AttachmentLink.auto_translated_fields
        }
        response = self.client.patch(
            reverse("AttachmentLink-detail", args=(self.project.id, link.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=link.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(AttachmentLink.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(AttachmentLink.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_link(self):
        self.client.force_authenticate(self.superadmin)
        link = AttachmentLinkFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=link.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("AttachmentLink-detail", args=(self.project.id, link.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=link.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
