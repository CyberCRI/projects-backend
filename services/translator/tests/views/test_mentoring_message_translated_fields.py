from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import MentorCreatedMentoringFactory
from apps.skills.models import Mentoring, MentoringMessage
from services.translator.models import AutoTranslatedField

faker = Faker()


class MentoringMessageTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.mentoring = MentorCreatedMentoringFactory(organization=cls.organization)
        cls.user = cls.mentoring.mentoree
        cls.content_type = ContentType.objects.get_for_model(MentoringMessage)

    def test_create_mentoring_message(self):
        self.client.force_authenticate(self.user)
        payload = {
            "status": Mentoring.MentoringStatus.PENDING.value,
            "content": faker.word(),
            "reply_to": faker.email(),
        }
        response = self.client.post(
            reverse(
                "Mentoring-respond", args=(self.organization.code, self.mentoring.id)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message = self.mentoring.messages.last()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=message.id
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(MentoringMessage._auto_translated_fields),
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(MentoringMessage._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)
