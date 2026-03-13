from unittest.mock import call, patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import TermsAndConditions
from services.translator.models import AutoTranslatedField
from services.translator.testcases import MockTranslateTestCase

faker = Faker()


class TermsAndConditionsTranslatedFieldsTestCase(MockTranslateTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(auto_translate_content=True)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(TermsAndConditions)

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_update_terms_and_conditions(self, mock_translate):
        mock_translate.side_effect = self.translator_side_effect
        self.client.force_authenticate(self.superadmin)
        terms_and_conditions = self.organization.terms_and_conditions
        payload = {"content": f"<p>{faker.text()}</p>"}
        response = self.client.patch(
            reverse(
                "TermsAndConditions-detail",
                args=(self.organization.code, terms_and_conditions.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=terms_and_conditions.id
        )
        self.assertEqual(
            auto_translated_fields.count(),
            len(TermsAndConditions._auto_translated_fields),
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(TermsAndConditions._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertTrue(field.up_to_date)
        terms_and_conditions.refresh_from_db()
        mock_translate.assert_has_calls(
            [
                call(
                    body=[
                        getattr(
                            terms_and_conditions,
                            field.split(":", 1)[1] if ":" in field else field,
                        )
                    ],
                    to_language=({str(lang) for lang in settings.REQUIRED_LANGUAGES}),
                    text_type=(field.split(":", 1)[0] if ":" in field else "plain"),
                )
                for field in TermsAndConditions.auto_translated_fields
            ],
            any_order=True,
        )
