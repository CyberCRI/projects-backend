from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import Project


@register(Project)
class ProjectTranslationOptions(TranslationOptions):
    fields = ("title", "description")
    required_languages = settings.REQUIRED_LANGUAGES
