from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from apps.projects.models import BlogEntry
from services.translator.models import AutoTranslatedField

faker = Faker()


class BlogEntryTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(BlogEntry)

    def test_create_blog_entry(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.word(),
            "content": faker.word(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(BlogEntry.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(BlogEntry.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_blog_entry(self):
        self.client.force_authenticate(self.superadmin)
        blog_entry = BlogEntryFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=blog_entry.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            BlogEntry.auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse("BlogEntry-detail", args=(self.project.id, blog_entry.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=blog_entry.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(BlogEntry.auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in BlogEntry.auto_translated_fields
        }
        response = self.client.patch(
            reverse("BlogEntry-detail", args=(self.project.id, blog_entry.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=blog_entry.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(BlogEntry.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(BlogEntry.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_blog_entry(self):
        self.client.force_authenticate(self.superadmin)
        blog_entry = BlogEntryFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=blog_entry.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("BlogEntry-detail", args=(self.project.id, blog_entry.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=blog_entry.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
