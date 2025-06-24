from typing import Dict

from django.contrib.contenttypes.models import ContentType

from .models import AutoTranslatedField


class HasAutoTranslatedFields:
    """
    A model that has fields that can be automatically translated.

    Models based on this mixin must implement a `Meta` class with the following
    attributes:
    - `translated_fields`: A list of field names that should be automatically translated.
    - `html_translated_fields`: A list of field names that should be automatically translated
      and are HTML fields.

    When the model is saved, it will check if any of the translated fields
    have changed. If they have, it will create or update an `AutoTranslatedField`
    instance for each field, marking it as not up to date. This allows the system
    to know that the translations need to be updated.
    """

    _original_translated_fields_values: Dict[str, str] = {}

    class Meta:
        translated_fields = []
        html_translated_fields = []

    def __init__(self, *args, **kwargs):
        self._original_translated_fields_values = {
            field: getattr(self, field, "")
            for field in self.Meta.translated_fields + self.Meta.html_translated_fields
        }
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Save the model instance and update the translated fields.
        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        for field in self.Meta.translated_fields + self.Meta.html_translated_fields:
            if getattr(self, field) != self._original_translated_fields_values[field]:
                AutoTranslatedField.objects.update_or_create(
                    content_type=content_type,
                    object_id=self.pk,
                    field_name=field,
                    defaults={
                        "up_to_date": False,
                        "html_field": field in self.Meta.html_translated_fields,
                    },
                )
        return super().save(*args, **kwargs)
