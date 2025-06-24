from typing import Union

from bs4 import BeautifulSoup, NavigableString

from apps.commons.mixins import OrganizationRelated

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
    languages = set(lang for org in organizations for lang in org.languages)
    if languages:
        translations = {
            f"{field_name}_{lang}": translate_content(
                content, lang, is_html=field.html_field
            )
            for lang in languages
        }
        instance._meta.model.objects.filter(pk=instance.pk).update(**translations)
    field.up_to_date = True
    field.save()


def translate_text_content(content: str, language: str) -> str:
    return content


def translate_html_content(content: Union[str, BeautifulSoup], language: str) -> str:
    if isinstance(content, str):
        soup = BeautifulSoup(content, features="html.parser")
    else:
        soup = content
    for child in soup.children:
        if isinstance(child, NavigableString):
            # Only translate non-empty, non-whitespace text nodes
            text_content = str(child)
            if text_content.strip():
                translated_text = translate_text_content(text_content, language)
                child.replace_with(translated_text)
        elif child.name is not None:
            translate_html_content(child, language)
    return str(soup)


def translate_content(content: str, language: str, is_html: bool = False) -> str:
    """
    Translate the content of an AutoTranslatedField to a specific language.
    """
    if is_html:
        return translate_html_content(content, language)
    return translate_text_content(content, language)
