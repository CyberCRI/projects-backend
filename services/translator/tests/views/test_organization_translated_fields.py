from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import Organization
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class OrganizationTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Organization)

    def test_create_organization(self):
        self.client.force_authenticate(self.superadmin)
        logo_image = self.get_test_image()
        payload = {
            "name": faker.word(),
            "code": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "website_url": faker.url(),
            "logo_image_id": logo_image.id,
        }
        response = self.client.post(reverse("Organization-list"), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Organization.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Organization.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_organization(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            Organization.auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Organization.auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in Organization.auto_translated_fields
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Organization.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Organization.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_organization(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("Organization-detail", args=(organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=organization.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
