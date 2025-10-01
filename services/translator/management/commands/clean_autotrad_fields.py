from django.conf import settings
from django.core.management import BaseCommand

from services.translator.interface import AzureTranslatorService
from services.translator.models import AutoTranslatedField


class Command(BaseCommand):
    def handle(self, *args, **options):
        for field in AutoTranslatedField.objects.all():
            instance = field.content_type.get_object_for_this_type(pk=field.object_id)
            field_name = field.field_name

            translations = {
                f"{field_name}_{lang}": getattr(instance, f"{field_name}_{lang}")
                for lang in settings.REQUIRED_LANGUAGES
            }
            updated_translations = {
                lang: AzureTranslatorService.clean_translation(text)
                for lang, text in translations.items()
            }
            instance._meta.model.objects.filter(pk=instance.pk).update(
                **updated_translations
            )
