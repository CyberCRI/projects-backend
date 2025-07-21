from django.conf import settings
from rest_framework import serializers


class AutoTranslatedModelSerializer(serializers.ModelSerializer):
    """
    Automatically include translations fields for models with `HasAutoTranslatedFields` mixin.

    Because these are automatically generated, they are read-only.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add translated fields to the read_only_fields
        fields = getattr(self.Meta, "fields", [])
        read_only_fields = getattr(self.Meta, "read_only_fields", [])
        translated_fields = getattr(self.Meta.model, "auto_translated_fields", [])
        for field in fields:
            if field in translated_fields:
                for lang in settings.REQUIRED_LANGUAGES:
                    read_only_fields.append(f"{field}_{lang}")
        self.Meta.read_only_fields = read_only_fields

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        # Get HasAutoTranslatedFields mixin auto_translated_fields
        translated_fields = getattr(self.Meta.model, "auto_translated_fields", [])
        all_fields = []
        for field in fields:
            all_fields.append(field)
            if field in translated_fields:
                for lang in settings.REQUIRED_LANGUAGES:
                    all_fields.append(f"{field}_{lang}")
        return all_fields

    class Meta:
        model = None
        read_only_fields = []
