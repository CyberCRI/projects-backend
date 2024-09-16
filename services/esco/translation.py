from django.conf import settings
from modeltranslation.translator import TranslationOptions, register

from .models import EscoOccupation, EscoSkill


@register(EscoSkill)
class EscoSkillTranslationOptions(TranslationOptions):
    fields = ("title", "description")
    required_languages = settings.REQUIRED_LANGUAGES


@register(EscoOccupation)
class EscoOccupationTranslationOptions(TranslationOptions):
    fields = ("title", "description")
    required_languages = settings.REQUIRED_LANGUAGES
