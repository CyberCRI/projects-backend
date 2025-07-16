from typing import Dict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .models import AutoTranslatedField


class TranslatedModelMeta(models.base.ModelBase):
    """
    Metaclass for models that have fields that can be automatically translated.
    It dynamically creates translated fields for each language specified in
    `settings.REQUIRED_LANGUAGES`.

    This allows us to avoid using the `django-modeltranslation` library while because
    it would force us to have the original value linked to the default language field.

    Using this metaclass, we can create fields like `title_en`, `title_fr`, while
    keeping the original field `title` as the default language field.
    """

    def __new__(cls, name, bases, attrs):
        for field in attrs.get("auto_translated_fields", []):
            base_field = attrs[field]
            for lang in settings.REQUIRED_LANGUAGES:
                attrs[f"{field}_{lang}"] = base_field.__class__(
                    *base_field.deconstruct()[2],
                    **{**base_field.deconstruct()[3], "blank": True, "null": True},
                )
        return super().__new__(cls, name, bases, attrs)


class HasAutoTranslatedFields(metaclass=TranslatedModelMeta):
    """
    A model that has fields that can be automatically translated.

    Models based on this mixin must implement the following attribute:
    - `auto_translated_fields`: A list of field names that should be automatically
      translated.

    When the model is saved, it will check if any of the translated fields
    have changed. If they have, it will create or update an `AutoTranslatedField`
    instance for each field, marking it as not up to date. This allows the system
    to know that the translations need to be updated.
    """

    auto_translated_fields = []
    _original_auto_translated_fields_values: Dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        self._original_auto_translated_fields_values = {
            field: getattr(self, field, "") for field in self.auto_translated_fields
        }
        super().__init__(*args, **kwargs)

    def update_translated_fields(self, force_update: bool = True):
        """
        Mark the translated fields as not up to date if they have changed. This method
        should be called whenever the model instance is updated.

        It can also be called explicitly if needed, for example to force trigger the
        update of translated fields without saving the model.

        Arguments:
            force_update (bool): If True, will update the translated fields even if they
                have not changed. Defaults to True.
        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        for field in self.auto_translated_fields:
            if (
                force_update
                or getattr(self, field)
                != self._original_auto_translated_fields_values[field]
            ):
                AutoTranslatedField.objects.update_or_create(
                    content_type=content_type,
                    object_id=self.pk,
                    field_name=field,
                    defaults={"up_to_date": False},
                )

    def save(self, *args, **kwargs):
        self.update_translated_fields(force_update=False)
        return super().save(*args, **kwargs)
