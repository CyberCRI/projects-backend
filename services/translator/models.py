import re

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.commons.mixins import OrganizationRelated

from .interface import AzureTranslatorService

AZURE_MAX_LENGTH = 50000


class AutoTranslatedField(models.Model):
    """
    Model to manage automatic translations for various content types.

    Attributes:
    ----------
        content_type: ForeignKey
            The content type of the related instance.
        object_id: CharField
            The ID of the related instance.
        field_name: CharField
            The name of the field to be translated.
        up_to_date: BooleanField
            Indicates if the translation is up to date.
    """

    class FieldType(models.TextChoices):
        PLAIN = "plain"
        HTML = "html"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    field_name = models.CharField(max_length=255)
    up_to_date = models.BooleanField(default=False)
    field_type = models.CharField(
        max_length=10, choices=FieldType.choices, default=FieldType.PLAIN
    )

    class Meta:
        unique_together = ("content_type", "object_id", "field_name")

    @property
    def instance(self) -> models.Model:
        """Return the related instance."""
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    @staticmethod
    def split_content(
        content: str, max_length: int, text_type: str = "plain"
    ) -> list[str] | list[BeautifulSoup]:
        """
        Split content into chunks of max_length, trying to split at html tags.

        Maximum length for Azure Translator is 50 000 characters per request accross all
        languages.

        For example, sending a translate request of 3 000 characters to translate to three
        different languages results in a request size of 3 000 x 3 = 9 000 characters

        This function splits the content into chunks either at the end of a html tag or
        at the last space before max_length.
        """
        if text_type == "html":
            soup = BeautifulSoup(content, "html.parser")
            return soup.find_all(recursive=False)

        if len(content) <= max_length:
            return [content]
        chunks = []
        start = 0
        while start < len(content):
            end = start + max_length
            if end >= len(content):
                chunks.append(content[start:])
                break
            split_at = content.rfind(" ", start, end)
            if split_at == -1 or split_at <= start:
                split_at = end
            chunks.append(content[start:split_at])
            start = split_at
        return chunks

    def update_translation(self):
        instance = self.instance
        field_name = self.field_name
        content = getattr(instance, field_name, "")
        if not isinstance(instance, OrganizationRelated):
            raise ValueError(
                f"{instance._meta.model.__name__} does not support translations. "
                "`OrganizationRelated` mixin is required for automatic translations."
            )
        if getattr(instance, "auto_translate_all_languages", False):
            languages = (
                settings.REQUIRED_LANGUAGES
                if any(
                    o.auto_translate_content
                    for o in instance.get_related_organizations()
                )
                else {}
            )
        else:
            organizations = [
                o
                for o in instance.get_related_organizations()
                if o.auto_translate_content
            ]
            # iter over languages in set (remove duplicate language)
            languages: set[str] = {
                lang for org in organizations for lang in org.languages
            }
        if languages:
            base_max_length = AZURE_MAX_LENGTH * 0.8  # Safety margin
            max_length = int(base_max_length // len(languages))
            if content:
                chunks = self.split_content(
                    content, max_length, text_type=self.field_type
                )
                translations = {}
                detected_languages = []
                for chunk in chunks:
                    if (
                        self.field_type == "html"
                        and (not str(chunk).strip() or not chunk.get_text(strip=True))
                    ) or (re.findall(r'data:image\/[a-zA-Z]+;base64,[^"\']+', content)):
                        chunk_translations = [
                            {"to": lang, "text": str(chunk)} for lang in languages
                        ]
                    else:
                        chunk = str(chunk)
                        if len(chunk) <= max_length:
                            chunk_translations, detected_language = (
                                AzureTranslatorService.translate_text_content(
                                    str(chunk), languages, self.field_type
                                )
                            )
                            detected_languages.append(detected_language)
                        elif len(chunk) < base_max_length:
                            for lang in languages:
                                lang_chunk_translation, detected_language = (
                                    AzureTranslatorService.translate_text_content(
                                        str(chunk), [lang], self.field_type
                                    )
                                )
                                chunk_translations.append(
                                    {
                                        "to": lang,
                                        "text": lang_chunk_translation[0]["text"],
                                    }
                                )
                                detected_languages.append(detected_language)
                        else:
                            chunk_translations = [
                                {"to": lang, "text": str(chunk)} for lang in languages
                            ]
                    translations = {
                        f"{field_name}_{translation['to']}": (
                            translations.get(f"{field_name}_{translation['to']}", "")
                            + translation["text"]
                        )
                        for translation in chunk_translations
                    }
                # Use the most common detected language among chunks
                if detected_languages:
                    detected_language = max(
                        set(detected_languages), key=detected_languages.count
                    )
                    translations[f"{field_name}_detected_language"] = detected_language
            else:
                translations = {f"{field_name}_{lang}": content for lang in languages}
            instance._meta.model.objects.filter(pk=instance.pk).update(**translations)
        self.up_to_date = True
        self.save()
