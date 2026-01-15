from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import LocationFactory, ProjectFactory
from apps.projects.models import Location
from services.translator.models import AutoTranslatedField

faker = Faker()


class LocationTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Location)

    def test_create_location(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.word(),
            "description": faker.word(),
            "lat": float(faker.latitude()),
            "lng": float(faker.longitude()),
            "type": Location.LocationType.TEAM,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Location-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Location._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Location._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_location(self):
        self.client.force_authenticate(self.superadmin)
        location = LocationFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=location.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            Location._auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse("Location-detail", args=(self.project.id, location.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=location.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Location._auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in Location._auto_translated_fields
        }
        response = self.client.patch(
            reverse("Location-detail", args=(self.project.id, location.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=location.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Location._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Location._auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_location(self):
        self.client.force_authenticate(self.superadmin)
        location = LocationFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=location.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("Location-detail", args=(self.project.id, location.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=location.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
