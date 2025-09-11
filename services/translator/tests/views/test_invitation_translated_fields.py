from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import InvitationFactory
from apps.invitations.models import Invitation
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class InvitationTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Invitation)

    def test_create_invitation(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "expire_at": make_aware(faker.date_time()),
            "description": faker.word(),
        }
        response = self.client.post(
            reverse("Invitation-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Invitation.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Invitation.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_invitation(self):
        self.client.force_authenticate(self.superadmin)
        invitation = InvitationFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=invitation.pk
        ).update(up_to_date=True)
        payload = {
            translated_field: faker.word()
            for translated_field in Invitation.auto_translated_fields
        }
        response = self.client.patch(
            reverse("Invitation-detail", args=(self.organization.code, invitation.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=invitation.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Invitation.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Invitation.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_invitation(self):
        self.client.force_authenticate(self.superadmin)
        invitation = InvitationFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=invitation.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("Invitation-detail", args=(self.organization.code, invitation.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=invitation.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
