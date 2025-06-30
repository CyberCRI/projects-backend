from apps.commons.mixins import OrganizationRelated

from .interface import AzureTranslatorService
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
    languages = list(set(lang for org in organizations for lang in org.languages))
    if languages:
        translations = AzureTranslatorService.translate_text_content(content, languages)
        translations = {
            f"translated_{field_name}_{translation['to']}": translation["text"]
            for translation in translations
        }
        instance._meta.model.objects.filter(pk=instance.pk).update(**translations)
    field.up_to_date = True
    field.save()
