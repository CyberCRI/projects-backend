from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import Email


@register(Email)
class EmailTranslationOptions(TranslationOptions):
    fields = (
        "subject",
        "content",
    )
    required_languages = settings.REQUIRED_LANGUAGES
