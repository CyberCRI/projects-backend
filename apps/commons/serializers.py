from django.conf import settings
from modeltranslation.manager import get_translatable_fields_for_model
from rest_framework import serializers
from rest_framework.settings import import_from_string


class EmailAddressSerializer(serializers.Serializer):
    email = serializers.EmailField()


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


class ProjectRelatedSerializer(serializers.ModelSerializer):
    """Base serializer for serializers related to projects."""

    model_project_field = "project"
    force_project_value = True
    forbid_project_update = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_project = self.context.get("project", None)
        self.current_organization = self.context.get("organization", None)

    def to_internal_value(self, data):
        if self.force_project_value:
            data[self.model_project_field] = self.current_project
        if self.instance and self.instance.pk and self.forbid_project_update:
            data.pop(self.model_project_field)
        return super().to_internal_value(data)


class OrganizationRelatedSerializer(serializers.ModelSerializer):
    """Base serializer for serializers related to organizations."""

    model_organization_field = "organization"
    force_organization_value = True
    forbid_organization_update = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_organization = self.context.get("organization", None)

    def to_internal_value(self, data):
        if self.force_organization_value:
            data[self.model_organization_field] = self.current_organization
        if self.instance and self.instance.pk and self.forbid_organization_update:
            data.pop(self.model_organization_field)
        return super().to_internal_value(data)


class PeopleGroupRelatedSerializer(ProjectRelatedSerializer):
    """Base serializer for serializers related to people groups."""

    model_people_group_field = "people_group"
    force_people_group_value = True
    forbid_people_group_update = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_people_group = self.context.get("people_group", None)
        self.current_organization = self.context.get("organization", None)

    def to_internal_value(self, data):
        if self.force_people_group_value:
            data[self.model_people_group_field] = self.current_people_group
        if self.instance and self.instance.pk and self.forbid_people_group_update:
            data.pop(self.model_people_group_field)
        return super().to_internal_value(data)
