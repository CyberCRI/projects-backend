from typing import List

from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings


class AzureTranslatorService:

    credentials = AzureKeyCredential(settings.AZURE_TRANSLATOR_KEY)
    service = TextTranslationClient(
        credential=credentials, region=settings.AZURE_TRANSLATOR_REGION
    )

    @classmethod
    def translate_text_content(cls, content: str, languages: List[str]) -> str:
        """
        Translate text content to the specified languages.
        """
        return cls.service.translate(body=[content], to_language=languages)[0][
            "translations"
        ]
