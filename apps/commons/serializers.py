from typing import Any, Collection, Dict, List, Optional

from django.conf import settings
from django.db.models import Model, Q
from modeltranslation.manager import get_translatable_fields_for_model
from rest_framework import mixins, serializers, viewsets
from rest_framework.settings import import_from_string

from apps.accounts.models import ProjectUser
from apps.commons.utils import process_text
from apps.files.models import Image
from apps.organizations.models import Organization
from apps.projects.models import Project


class ProjectRelatedSerializer(serializers.ModelSerializer):
    """Base serializer for serializers related to projects."""

    def get_related_project(self) -> Optional[Project]:
        """Retrieve the related projects"""
        raise NotImplementedError()


class OrganizationRelatedSerializer(serializers.ModelSerializer):
    """Base serializer for serializers related to organizations."""

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        raise NotImplementedError()


class EmailAddressSerializer(serializers.Serializer):
    email = serializers.EmailField()


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
        translated_fields = get_translatable_fields_for_model(self.Meta.model) or []
        all_fields = []

        requested_langs = []
        if "request" in self.context:
            lang_param = self.context["request"].query_params.get("lang")
            requested_langs = lang_param.split(",") if lang_param else []

        for field in fields:
            all_fields.append(field)
            if field in translated_fields:
                for lang in settings.REQUIRED_LANGUAGES:
                    if not requested_langs or lang in requested_langs:
                        all_fields.append(f"{field}_{lang}")
        return all_fields

    class Meta:
        model = None


class RetrieveUpdateModelViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    A viewset that provides `retrieve`, `list`, `update` and `partial_update`
    actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class ReadUpdateModelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `retrieve`, `list`, `update` and `partial_update`
    actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class CreateListModelViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `list` and `create` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class StringsImagesSerializer(serializers.ModelSerializer):
    """
    A base serializer that safely processes base64 images in text fields.
    It replaces base64 images with uploaded image references during serialization.
    """

    string_images_fields: List[str] = []
    string_images_forbid_fields: List[str] = []
    string_images_upload_to: str = ""
    string_images_view: str = ""
    string_images_process_template: bool = False
    string_images_field_name: str = "images"

    def get_string_images_kwargs(
        self, instance: Model, field_name: str, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        """Get additional kwargs for image processing based on the instance."""
        return {}

    def get_string_images_owner(
        self, instance: Model, field_name: str, *args: Any, **kwargs: Any
    ) -> Optional[ProjectUser]:
        """Get the owner for image processing based on the instance."""
        request = self.context.get("request")
        return request.user if request else None

    def add_string_images_to_instance(
        self, instance: Model, images: List["Image"]
    ) -> None:
        """Add images to the instance's images field."""
        if self.instance and images:
            field = getattr(self.instance, self.string_images_field_name, None)
            if field:
                field.add(*images)
        return instance

    def save(self, **kwargs):
        create = not self.instance
        updated = False
        images = []
        if create:
            super().save(**kwargs)
        for field in self.string_images_fields:
            if field in self.validated_data:
                content = self.validated_data[field]
                owner = self.get_string_images_owner(self.instance, field)
                image_kwargs = self.get_string_images_kwargs(self.instance, field)
                updated_content, images_to_add = process_text(
                    text=content,
                    instance=self.instance,
                    upload_to=self.string_images_upload_to,
                    view=self.string_images_view,
                    owner=owner,
                    process_template=self.string_images_process_template,
                    **image_kwargs,
                )
                if updated_content != content:
                    updated = True
                self.validated_data[field] = updated_content
                images.extend(images_to_add)
        for field in self.string_images_forbid_fields:
            if field in self.validated_data:
                content = self.validated_data[field]
                new_content, _ = process_text(content, forbid_images=True)
                if new_content != content:
                    updated = True
                self.validated_data[field] = new_content

        if create and not images and not updated:
            return self.instance
        instance = super().save(**kwargs)
        return self.add_string_images_to_instance(instance, images)
