from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import Project


@register(Project)
class ProjectTranslationOptions(TranslationOptions):
    fields = ("translated_title", "translated_description")
    required_languages = settings.REQUIRED_LANGUAGES
