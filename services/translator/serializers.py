from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ALL_FIELDS

from services.translator.mixins import HasAutoTranslatedFields


def auto_translated(cls: serializers.ModelSerializer) -> serializers.ModelSerializer:
    """Automatically include translations fields for models with `HasAutoTranslatedFields` mixin.

    Because these are automatically generated, they are read-only.
    """

    model = cls.Meta.model

    assert issubclass(
        model, HasAutoTranslatedFields
    ), "You model need to inherit from 'HasAutoTranslatedFields'"

    # model translated field name
    auto_translated_fields = model._auto_translated_fields

    fields_available = []
    for name in cls().get_fields():
        if name in auto_translated_fields:
            fields_available.append(name)

    # not fields is needed
    if not fields_available:
        return cls

    # generates all fields
    fields_to_add = [f"{field}_detected_language" for field in fields_available]
    for field in fields_available:
        fields_to_add.extend(f"{field}_{lang}" for lang in settings.REQUIRED_LANGUAGES)

    # set all fields in read_only (use set to avoid duplicated refered)
    read_only_fields = getattr(cls.Meta, "read_only_fields", [])
    cls.Meta.read_only_fields = tuple(set(read_only_fields) | set(fields_to_add))

    # set all fields in fields
    fields = getattr(cls.Meta, "fields", None)
    # if fields is set (can be None for exlucde content) and field is not "__all__" value
    # (use set to avoid duplicated redered field)
    if fields and fields != ALL_FIELDS:
        cls.Meta.fields = tuple(set(fields) | set(fields_to_add))

    return cls
