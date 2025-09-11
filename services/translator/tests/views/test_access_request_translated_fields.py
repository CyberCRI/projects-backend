from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import AccessRequestFactory
from apps.invitations.models import AccessRequest
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class AccessRequestTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(AccessRequest)

    def test_create_access_request(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.word(),
            "message": faker.word(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(AccessRequest.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(AccessRequest.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)
