from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import SeedUserFactory, UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class UserTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(ProjectUser)

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_create_user(self, mocked):
        mocked.return_value = {}
        self.client.force_authenticate(self.superadmin)
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.word(),
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectUser._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectUser._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_user(self):
        self.client.force_authenticate(self.superadmin)
        user = SeedUserFactory()
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=user.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            ProjectUser._auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.pk,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=user.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectUser._auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in ProjectUser._auto_translated_fields
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.pk,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=user.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectUser._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectUser._auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_user(self):
        self.client.force_authenticate(self.superadmin)
        user = UserFactory()
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=user.pk
        ).update(up_to_date=True)

        response = self.client.delete(reverse("ProjectUser-detail", args=(user.pk,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=user.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
