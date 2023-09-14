from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import Notification


@register(Notification)
class TagTranslationOptions(TranslationOptions):
    fields = ("reminder_message",)
    required_languages = settings.REQUIRED_LANGUAGES
