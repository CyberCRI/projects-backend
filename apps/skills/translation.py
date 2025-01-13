from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import Tag


@register(Tag)
class TagTranslationOptions(TranslationOptions):
    fields = ("title", "description", "alternative_titles")
    required_languages = settings.REQUIRED_LANGUAGES
