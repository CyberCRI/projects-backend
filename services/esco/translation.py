from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import EscoTag


@register(EscoTag)
class EscoTagTranslationOptions(TranslationOptions):
    fields = ("title", "description")
    required_languages = settings.REQUIRED_LANGUAGES
