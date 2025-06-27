import copy
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, NavigableString

from apps.commons.mixins import OrganizationRelated

from .interface import AzureTranslatorService
from .models import AutoTranslatedField


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
    languages = list(set(lang for org in organizations for lang in org.languages))
    if languages:
        translations = translate_content(content, languages, is_html=field.html_field)
        translations = {
            f"{field_name}_{translation['to']}": translation["text"]
            for translation in translations
        }
        instance._meta.model.objects.filter(pk=instance.pk).update(**translations)
    field.up_to_date = True
    field.save()


def translate_text_content(content: str, languages: List[str]) -> str:
    return AzureTranslatorService.translate_text_content(content, languages)


def get_html_translations(
    soup: BeautifulSoup, languages: List[str], translations: Optional[Dict] = None
) -> Dict:
    if translations is None:
        translations = {}
    for child in soup.children:
        if isinstance(child, NavigableString):
            # Only translate non-empty, non-whitespace text nodes
            text_content = str(child)
            if text_content.strip():
                translated_texts = translate_text_content(text_content, languages)
                translations[text_content] = translated_texts
        elif child.name is not None:
            get_html_translations(child, languages, translations)
    return {
        key: {value["to"]: value["text"] for value in values}
        for key, values in translations.items()
    }


def _translate_html_content(
    soup: BeautifulSoup, language: str, translations: Dict[str, Dict[str, str]]
) -> str:
    for child in soup.children:
        if isinstance(child, NavigableString):
            # Only translate non-empty, non-whitespace text nodes
            text_content = str(child)
            if text_content.strip():
                translated_text = translations.get(text_content, {}).get(
                    language, text_content
                )
                child.replace_with(translated_text)
        elif child.name is not None:
            _translate_html_content(child, language, translations)
    return str(soup)


def translate_html_content(content: str, languages: List[str]) -> str:
    soup = BeautifulSoup(content, features="html.parser")
    translations = get_html_translations(soup, languages) or {}
    return [
        {
            "to": lang,
            "text": _translate_html_content(copy.deepcopy(soup), lang, translations),
        }
        for lang in languages
    ]


def translate_content(content: str, languages: List[str], is_html: bool = False) -> str:
    """
    Translate the content of an AutoTranslatedField to a specific language.
    """
    if is_html:
        return translate_html_content(content, languages)
    return translate_text_content(content, languages)
