from typing import Dict, List
from unittest.mock import call, patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from faker import Faker

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.translator.models import AutoTranslatedField
from services.translator.tasks import automatic_translations

faker = Faker()


class UpdateTranslationsTestCase(JwtAPITestCase):
    @classmethod
    def translator_side_effect(
        cls, body: List[str], to_language: List[str]
    ) -> List[Dict]:
        """
        This side effect is meant to be used with unittest mock. It will mock every call
        made to the Azure translator API.

        Arguments
        ---------
        - content (str): The text content to be translated.
        - languages (list of str): The target languages for translation.

        Returns
        -------
        - A json response that simulates the Azure translator API response.
        """

        return [
            {
                "detectedLanguage": {"language": "en", "score": 1.0},
                "translations": [
                    {"text": f"{lang} : {body[0]}", "to": lang} for lang in to_language
                ],
            }
        ]

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_update_translated_fields(self, mock_translate):
        mock_translate.side_effect = self.translator_side_effect

        organization_1 = OrganizationFactory(auto_translate_content=True)
        organization_2 = OrganizationFactory(auto_translate_content=False)
        title = faker.sentence()
        description = faker.sentence()
        project_1 = ProjectFactory(
            organizations=[organization_1], title=title, description=description
        )
        project_2 = ProjectFactory(
            organizations=[organization_1], title=title, description=description
        )
        project_3 = ProjectFactory(
            organizations=[organization_2], title=title, description=description
        )

        AutoTranslatedField.objects.filter(
            content_type=ContentType.objects.get_for_model(Project),
            object_id=project_2.pk,
        ).update(up_to_date=True)

        automatic_translations()

        mock_translate.assert_has_calls(
            [
                call(
                    body=[title],
                    to_language=[str(lang) for lang in organization_1.languages],
                ),
                call(
                    body=[description],
                    to_language=[str(lang) for lang in organization_1.languages],
                ),
            ]
        )

        project_1.refresh_from_db()
        project_2.refresh_from_db()
        project_3.refresh_from_db()

        self.assertEqual(
            AutoTranslatedField.objects.filter(up_to_date=False).count(), 0
        )
        for project in [project_1, project_2, project_3]:
            self.assertEqual(project.title, title)
            self.assertEqual(project.description, description)
        for lang in settings.REQUIRED_LANGUAGES:
            if lang in organization_1.languages:
                self.assertEqual(
                    getattr(project_1, f"title_{lang}"), f"{lang} : {title}"
                )
                self.assertEqual(
                    getattr(project_1, f"description_{lang}"), f"{lang} : {description}"
                )
            else:
                self.assertIsNone(getattr(project_1, f"title_{lang}"))
                self.assertEqual(getattr(project_1, f"description_{lang}"), "")
            self.assertIsNone(getattr(project_2, f"title_{lang}"))
            self.assertEqual(getattr(project_2, f"description_{lang}"), "")
            self.assertIsNone(getattr(project_3, f"title_{lang}"))
            self.assertEqual(getattr(project_3, f"description_{lang}"), "")
