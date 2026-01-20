from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.organizations.models import ProjectCategory
from services.translator.models import AutoTranslatedField

faker = Faker()


class CategoryTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(ProjectCategory)

    def test_create_project_category(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "organization_code": self.organization.code,
            "name": faker.word(),
            "description": faker.word(),
        }
        response = self.client.post(
            reverse("Category-list", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectCategory._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectCategory._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_project_category(self):
        self.client.force_authenticate(self.superadmin)
        project_category = ProjectCategoryFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_category.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            ProjectCategory._auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse(
                "Category-detail", args=(self.organization.code, project_category.pk)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_category.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectCategory._auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in ProjectCategory._auto_translated_fields
        }
        response = self.client.patch(
            reverse(
                "Category-detail", args=(self.organization.code, project_category.pk)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_category.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectCategory._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectCategory._auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_project_category(self):
        self.client.force_authenticate(self.superadmin)
        project_category = ProjectCategoryFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_category.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse(
                "Category-detail", args=(self.organization.code, project_category.pk)
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_category.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
