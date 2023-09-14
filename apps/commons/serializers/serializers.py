from typing import Collection

from django.conf import settings
from django.db.models import Q
from modeltranslation.manager import get_translatable_fields_for_model
from rest_framework import serializers
from rest_framework.settings import import_from_string


class FilteredListSerializer(serializers.ListSerializer):
    """`ListSerializer` which accepts a list of Q objects to filter the data."""

    def __init__(self, *args, filters: Collection[Q] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = filters

    def to_representation(self, data):
        data = data.all()
        if self.filters:
            data = data.filter(*self.filters)
        return super().to_representation(data)


class LazySerializer(serializers.Serializer):
    """Allows to define a lazy serializer.
    This can be useful to circumvent circular imports.
    Take a dotted reference to a serializer, any remaining `args` and `kwargs`
    are passed down to the serializer.
    """

    def __init__(self, ref, *args, **kwargs):  # noqa
        self._args = args
        self._kwargs = kwargs
        self._reference_as_string = ref
        self._reference_as_serializer = None

    def __getattr__(self, item):
        return getattr(self._reference_as_serializer, item)

    def __getattribute__(self, attr):
        attrs = [
            "_args",
            "_kwargs",
            "_reference_as_string",
            "_reference_as_serializer",
            "_creation_counter",
        ]
        # _creation_counter is called when initializing the serializer which uses this LazyRefSerializer field
        if attr not in attrs and self._reference_as_serializer is None:
            referenced_serializer = import_from_string(self._reference_as_string, "")
            self._reference_as_serializer = referenced_serializer(
                *self._args, **self._kwargs
            )
            self.__class__ = referenced_serializer
            self.__dict__.update(self._reference_as_serializer.__dict__)
        return object.__getattribute__(self, attr)


class TranslatedModelSerializer(serializers.ModelSerializer):
    """
    Automatically translate model fields for model with registered translation
    """

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        trans_fields = get_translatable_fields_for_model(self.Meta.model)
        all_fields = []

        requested_langs = []
        if "request" in self.context:
            lang_param = self.context["request"].query_params.get("lang", None)
            requested_langs = lang_param.split(",") if lang_param else []

        for f in fields:
            if f not in trans_fields:
                all_fields.append(f)
            else:
                all_fields.append(f)
                for lang_code in settings.REQUIRED_LANGUAGES:
                    if not requested_langs or lang_code in requested_langs:
                        all_fields.append("{}_{}".format(f, lang_code))

        return all_fields

    class Meta:
        model = None
