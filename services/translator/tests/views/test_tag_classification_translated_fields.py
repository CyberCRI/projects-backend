from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import TagClassificationFactory
from apps.skills.models import TagClassification
from services.translator.models import AutoTranslatedField

faker = Faker()


class TagClassificationTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(TagClassification)

    def test_create_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "is_public": faker.boolean(),
            "title": faker.word(),
            "description": faker.word(),
        }
        response = self.client.post(
            reverse("TagClassification-list", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(TagClassification.auto_translated_fields),
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(TagClassification.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        tag_classification = TagClassificationFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=tag_classification.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            TagClassification.auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse(
                "TagClassification-detail",
                args=(self.organization.code, tag_classification.pk),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=tag_classification.pk
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(TagClassification.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in TagClassification.auto_translated_fields
        }
        response = self.client.patch(
            reverse(
                "TagClassification-detail",
                args=(self.organization.code, tag_classification.pk),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=tag_classification.pk
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(TagClassification.auto_translated_fields),
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(TagClassification.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        tag_classification = TagClassificationFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=tag_classification.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse(
                "TagClassification-detail",
                args=(self.organization.code, tag_classification.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=tag_classification.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
