from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings


class AzureTranslatorService:

    credentials = AzureKeyCredential(settings.AZURE_TRANSLATOR_KEY)
    service = TextTranslationClient(
        credential=credentials,
        region=settings.AZURE_TRANSLATOR_REGION,
        endpoint=settings.AZURE_TRANSLATOR_ENDPOINT,
    )

    @classmethod
    def clean_translation(cls, text: str | None) -> str | None:
        if text:
            return text.replace("\xa0»", '"').replace("\xa0", "")
        return text

    @classmethod
    def translate_text_content(
        cls, content: str, languages: list[str], field_type: str
    ) -> tuple[list[dict], str]:
        """
        Translate text content to the specified languages.
        """
        response = cls.service.translate(
            body=[content],
            to_language=set(languages),
            text_type=field_type.lower(),
        )
        response = response[0]
        detected_language = response.detected_language.language
        translations = response.translations
        translations = [
            {"to": translation.to, "text": cls.clean_translation(translation.text)}
            for translation in translations
        ]
        return translations, detected_language
