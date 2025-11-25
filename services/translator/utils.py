import re
from typing import List, Union

from bs4 import BeautifulSoup

from apps.commons.mixins import OrganizationRelated

from .interface import AzureTranslatorService
from .models import AutoTranslatedField


def split_content(
    content: str,
    languages: list[str],
    max_length: int = 50000,
    text_type: str = "plain",
) -> Union[List[str], List[BeautifulSoup]]:
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

    max_length = int(max_length // (len(languages) * 1.2))  # Safety margin
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


def update_auto_translated_field(field: AutoTranslatedField):
    instance = field.instance
    field_name = field.field_name
    content = getattr(instance, field_name, "")
    if re.findall(r'data:image\/[a-zA-Z]+;base64,[^"\']+', content):
        raise ValueError(
            "Content contains base64 encoded images which cannot be translated."
        )
    if len(content) > 100000:
        raise ValueError(
            f"Content length for field {field_name} exceeds 100 000 characters. "
            "Automatic translation cannot be performed."
        )
    if not isinstance(instance, OrganizationRelated):
        raise ValueError(
            f"{instance._meta.model.__name__} does not support translations. "
            "`OrganizationRelated` mixin is required for automatic translations."
        )
    organizations = [
        o for o in instance.get_related_organizations() if o.auto_translate_content
    ]
    languages = list(
        dict.fromkeys([lang for org in organizations for lang in org.languages])
    )
    if languages:
        if content:
            chunks = split_content(content, languages, text_type=field.field_type)
            translations = {}
            detected_language = None
            for chunk in chunks:
                # If HTML, skip translation for tags with no text content (empty or whitespace only)
                if field.field_type == "html" and (
                    not str(chunk).strip() or not chunk.get_text(strip=True)
                ):
                    chunk_translations, detected_language = (
                        [{"to": lang, "text": str(chunk)} for lang in languages],
                        detected_language,
                    )
                else:
                    chunk_translations, detected_language = (
                        AzureTranslatorService.translate_text_content(
                            str(chunk), languages, field.field_type
                        )
                    )
                translations = {
                    f"{field_name}_{translation['to']}": (
                        translations.get(f"{field_name}_{translation['to']}", "")
                        + translation["text"]
                    )
                    for translation in chunk_translations
                }
                translations[f"{field_name}_detected_language"] = detected_language
            translations[f"{field_name}_detected_language"] = detected_language
        else:
            translations = {f"{field_name}_{lang}": content for lang in languages}
        instance._meta.model.objects.filter(pk=instance.pk).update(**translations)
    field.up_to_date = True
    field.save()
