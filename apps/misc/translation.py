from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import WikipediaTag


@register(WikipediaTag)
class TagTranslationOptions(TranslationOptions):
    fields = ("name",)
    required_languages = settings.REQUIRED_LANGUAGES
