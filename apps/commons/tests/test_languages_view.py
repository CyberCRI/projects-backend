from django.conf import settings
from django.urls import reverse
from rest_framework import status

from apps.commons.enums import Language
from apps.commons.test import JwtAPITestCase


class GetLanguagesTestCase(JwtAPITestCase):
    def test_get_languages(self):
        response = self.client.get(reverse("Languages"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), len(settings.LANGUAGES))
        self.assertEqual(len(content), len(Language.__members__))
        self.assertSetEqual(
            {(lang["code"], lang["name"]) for lang in content},
            set(settings.LANGUAGES),
        )
        self.assertSetEqual(
            {(lang["code"], lang["name"]) for lang in content},
            {(lang.value, lang.label) for lang in Language},
        )
