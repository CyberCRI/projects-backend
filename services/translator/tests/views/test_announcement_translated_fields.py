from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class AnnouncementTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Announcement)

    def test_create_announcement(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Announcement.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Announcement.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_announcement(self):
        self.client.force_authenticate(self.superadmin)
        announcement = AnnouncementFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=announcement.pk
        ).update(up_to_date=True)

        payload = {
            translated_field: faker.word()
            for translated_field in Announcement.auto_translated_fields
        }
        response = self.client.patch(
            reverse("Announcement-detail", args=(self.project.id, announcement.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=announcement.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Announcement.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Announcement.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_announcement(self):
        self.client.force_authenticate(self.superadmin)
        announcement = AnnouncementFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=announcement.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("Announcement-detail", args=(self.project.id, announcement.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=announcement.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
