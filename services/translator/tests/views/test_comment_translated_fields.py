from unittest.mock import call, patch

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.feedbacks.factories import CommentFactory
from apps.feedbacks.models import Comment
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.translator.models import AutoTranslatedField
from services.translator.testcases import MockTranslateTestCase

faker = Faker()


class CommentTranslatedFieldsTestCase(MockTranslateTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(auto_translate_content=True)
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Comment)

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_create_comment(self, mock_translate):
        mock_translate.side_effect = self.translator_side_effect

        self.client.force_authenticate(self.superadmin)
        payload = {"content": f"<p>{faker.text()}</p>", "project_id": self.project.id}
        response = self.client.post(
            reverse("Comment-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Comment._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Comment._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertTrue(field.up_to_date)
        comment = Comment.objects.get(id=content["id"])
        mock_translate.assert_has_calls(
            [
                call(
                    body=[
                        getattr(
                            comment,
                            field.split(":", 1)[1] if ":" in field else field,
                        )
                    ],
                    to_language=({str(lang) for lang in self.organization.languages}),
                    text_type=(field.split(":", 1)[0] if ":" in field else "plain"),
                )
                for field in Comment.auto_translated_fields
            ],
            any_order=True,
        )

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_update_comment(self, mock_translate):
        mock_translate.side_effect = self.translator_side_effect

        self.client.force_authenticate(self.superadmin)
        comment = CommentFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=comment.pk
        ).update(up_to_date=True)

        payload = {
            translated_field: (
                f"<p>{faker.word()}</p>"
                if translated_field in Comment._html_auto_translated_fields
                else faker.word()
            )
            for translated_field in Comment._auto_translated_fields
        }
        response = self.client.patch(
            reverse("Comment-detail", args=(self.project.id, comment.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=comment.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Comment._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Comment._auto_translated_fields),
        )

        for field in auto_translated_fields:
            self.assertTrue(field.up_to_date)
        comment.refresh_from_db()
        mock_translate.assert_has_calls(
            [
                call(
                    body=[
                        getattr(
                            comment,
                            field.split(":", 1)[1] if ":" in field else field,
                        )
                    ],
                    to_language=({str(lang) for lang in self.organization.languages}),
                    text_type=(field.split(":", 1)[0] if ":" in field else "plain"),
                )
                for field in Comment.auto_translated_fields
            ],
            any_order=True,
        )

    def test_delete_comment(self):
        self.client.force_authenticate(self.superadmin)
        comment = CommentFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=comment.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, comment.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=comment.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
