import copy

from django.conf import settings
from modeltranslation.manager import get_translatable_fields_for_model
from rest_framework import serializers
from rest_framework.serializers import ALL_FIELDS

from services.translator.mixins import HasAutoTranslatedFields


def generate_translated_fields(fields_names: tuple[str]):
    def _wraps(cls: serializers.BaseSerializer) -> serializers.BaseSerializer:

        # generates all fields
        for field in fields_names:
            for lang in settings.REQUIRED_LANGUAGES:
                field_name = f"{field}_{lang}"
                duplicate = copy.deepcopy(cls._declared_fields[field])
                cls._declared_fields[field_name] = duplicate

        return cls

    return _wraps


def auto_translated(cls: serializers.ModelSerializer) -> serializers.ModelSerializer:
    """Automatically include translations fields for models with `HasAutoTranslatedFields` mixin.

    Because these are automatically generated, they are read-only.
    """

    model = cls.Meta.model

    assert issubclass(
        model, HasAutoTranslatedFields
    ), f"You model ({model}) need to inherit 'HasAutoTranslatedFields'"

    # model translated field name
    auto_translated_fields = model._auto_translated_fields

    fields_available = []
    for name in cls().get_fields():
        if name in auto_translated_fields:
            fields_available.append(name)

    # not fields is needed
    if not fields_available:
        return cls

    fields_to_add = [f"{field}_detected_language" for field in fields_available]
    # generates all fields
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


def external_auto_translated(
    cls: serializers.ModelSerializer,
) -> serializers.ModelSerializer:
    """Automatically include translations fields for models with from `modeltranslation` lib.

    all field generated is not read-only (cant be set from serializer).
    """

    model = cls.Meta.model

    auto_translated_fields = get_translatable_fields_for_model(model)
    assert (
        auto_translated_fields is not None
    ), f"You model ({model}) need to register from 'modeltranslation'"

    fields_available = []
    for name in cls().get_fields():
        if name in auto_translated_fields:
            fields_available.append(name)

    # not fields is needed
    if not fields_available:
        return cls

    fields_to_add = []
    # generates all fields
    for field in fields_available:
        fields_to_add.extend(f"{field}_{lang}" for lang in settings.REQUIRED_LANGUAGES)

    # set all fields in fields
    fields = getattr(cls.Meta, "fields", None)
    # if fields is set (can be None for exlucde content) and field is not "__all__" value
    # (use set to avoid duplicated redered field)
    if fields and fields != ALL_FIELDS:
        cls.Meta.fields = tuple(set(fields) | set(fields_to_add))

    return cls
