from apps.commons.mixins import OrganizationRelated

from .interface import AzureTranslatorService
from .models import AutoTranslatedField


def split_content(
    content: str, languages: list[str], max_length: int = 50000
) -> list[str]:
    """
    Split content into chunks of max_length, trying to split at html tags.

    Maximum length for Azure Translator is 50 000 characters per request accross all
    languages.

    For example, sending a translate request of 3 000 characters to translate to three
    different languages results in a request size of 3 000 x 3 = 9 000 characters

    This function splits the content into chunks either at the end of a html tag or
    at the last space before max_length.
    """
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
        split_at = content.rfind("</", start, end)
        if split_at == -1 or split_at <= start:
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
            chunks = split_content(content, languages)
            translations = {}
            for chunk in chunks:
                chunk_translations, detected_language = (
                    AzureTranslatorService.translate_text_content(chunk, languages)
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
