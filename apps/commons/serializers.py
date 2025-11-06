from typing import Any, Collection, Dict, List, Optional

from django.conf import settings
from django.db.models import Q
from modeltranslation.manager import get_translatable_fields_for_model
from rest_framework import mixins, serializers, viewsets
from rest_framework.settings import import_from_string

from apps.accounts.models import ProjectUser
from apps.commons.utils import process_text
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
            lang_param = self.context["request"].query_params.get("lang", None)
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


class SafeBase64Serializer(serializers.ModelSerializer):
    """
    A base serializer that safely processes base64 images in text fields.
    It replaces base64 images with uploaded image references during serialization.
    """

    _images_fields: List[str] = []
    _forbid_images_fields: List[str] = []
    _images_upload_to: str = ""
    _images_view: str = ""
    _process_template: bool = False

    def _get_image_kwargs(self, instance: Any, field_name: str) -> Dict[str, Any]:
        """Get additional kwargs for image processing based on the instance."""
        raise NotImplementedError()

    def _get_image_owner(self, instance: Any) -> Optional[ProjectUser]:
        """Get the owner for image processing based on the instance."""
        request = self.context.get("request")
        return request.user if request else None

    def save(self, **kwargs):
        create = not self.instance
        updated = False
        images = []
        if create:
            super().save(**kwargs)
        for field in self._images_fields:
            if field in self.validated_data:
                content = self.validated_data[field]
                owner = self._get_image_owner(self.instance)
                kwargs = self._get_image_kwargs(self.instance)
                text, _images = process_text(
                    text=content,
                    instance=self.instance,
                    upload_to=self._images_upload_to,
                    view=self._images_view,
                    owner=owner,
                    process_template=self._process_template,
                    **kwargs,
                )
                if text != content:
                    updated = True
                self.validated_data[field] = text
                images.extend(_images)
        for field in self._forbid_images_fields:
            if field in self.validated_data:
                content = self.validated_data[field]
                new_content, _ = process_text(content, forbid_images=True)
                if new_content != content:
                    updated = True
                self.validated_data[field] = new_content

        if create and not images and not updated:
            return self.instance

        self.validated_data["description"] = text
        self.validated_data["images"] = images + [
            image for image in self.instance.images.all()
        ]
        return super().save(**kwargs)
