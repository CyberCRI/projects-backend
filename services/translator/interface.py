from typing import List, Tuple

from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings


class AzureTranslatorService:

    credentials = AzureKeyCredential(settings.AZURE_TRANSLATOR_KEY)
    service = TextTranslationClient(
        credential=credentials, region=settings.AZURE_TRANSLATOR_REGION
    )

    @classmethod
    def translate_text_content(cls, content: str, languages: List[str]) -> Tuple[List[dict], str]:
        """
        Translate text content to the specified languages.
        """
        response = cls.service.translate(body=[content], to_language=languages)
        response = response[0]
        return response["translations"], response["detectedLanguage"]["language"]
