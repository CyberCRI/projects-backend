from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class PeopleGroupTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(PeopleGroup)

    def test_create_people_group(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(auto_translated_fields.count(), 3)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(PeopleGroup.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_people_group(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=people_group.pk
        ).update(up_to_date=True)

        payload = {
            "title": faker.sentence(),
            "description": faker.sentence(),
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=people_group.pk
        )
        self.assertEqual(auto_translated_fields.count(), 3)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(PeopleGroup.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_people_group(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=people_group.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=people_group.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
