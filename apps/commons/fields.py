import inspect
from contextlib import suppress

from django.contrib.auth.models import Group
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import Field
from rest_framework.serializers import BaseSerializer

from apps.accounts.models import PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group


@extend_schema_field(OpenApiTypes.UUID)
class UserMultipleIdRelatedField(serializers.RelatedField):
    """
    A read-write field that allows multiple ids to be used to represent a user.

    Possible ids are:
        - id
        - slug
        - keycloak_id
    """

    default_error_messages = {
        "required": _("This field is required."),
        "does_not_exist": _('Invalid id "{user_id}" - object does not exist.'),
        "incorrect_type": _(
            "Incorrect type. Expected str value, received {data_type}."
        ),
    }

    def __init__(self, **kwargs):
        self.user_lookup = kwargs.pop("user_lookup", "")
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            lookup_field = ProjectUser.get_id_field_name(data)
            if self.user_lookup:
                lookup_field = f"{self.user_lookup}__{lookup_field}"
            return get_object_or_404(queryset, **{lookup_field: data})
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(data).__name__)

    def to_representation(self, value):
        return value.id


@extend_schema_field(OpenApiTypes.NONE)
class RecursiveField(Field):
    """A field that gets its representation from its parent.

    Can be used to serialize acyclic recursive structure, such as Acyclic Graph,
    Tree, LinkedList...

    Examples
    --------
    class TreeSerializer(serializers.Serializer):
        children = RecursiveField(many=True)
    class ListSerializer(serializers.Serializer):
        next = RecursiveField(allow_null=True)
    """

    # Attributes called by `rest_framework.serializers`
    PROXY_ATTRS = (
        # methods
        "get_value",
        "get_initial",
        "run_validation",
        "get_attribute",
        "to_representation",
        # attributes
        "field_name",
        "source",
        "read_only",
        "default",
        "source_attrs",
        "write_only",
    )

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self._proxy = None
        self.bind_args = None

        # Call super-constructor to support ModelSerializer
        super_kwargs = dict(
            (key, kwargs[key])
            for key in kwargs
            if key in inspect.signature(Field.__init__).parameters
        )
        super(RecursiveField, self).__init__(**super_kwargs)

    def __getattribute__(self, name):
        if name in RecursiveField.PROXY_ATTRS:
            try:
                proxy = object.__getattribute__(self, "proxy")
                return getattr(proxy, name)
            except AttributeError:
                pass

        return object.__getattribute__(self, name)

    def bind(self, field_name, parent):
        """Lazy binding.

        Avoid error when nested in a `ListField` (the `RecursiveField` will be
        bound before the `ListField` is bound)."""
        self.bind_args = (field_name, parent)

    @property
    def proxy(self) -> None:
        if self._proxy is not None or not self.bind_args:
            return self._proxy

        field_name, parent = self.bind_args

        if hasattr(parent, "child") and parent.child is self:
            # RecursiveField nested inside of a ListField
            parent_class = parent.parent.__class__
        else:
            # RecursiveField directly inside a Serializer
            parent_class = parent.__class__

        if not issubclass(parent_class, BaseSerializer):
            raise TypeError(
                f"{self.__class__.__name__} must be used insde a DRF serializer"
            )

        proxy_class = parent_class

        # Create a new serializer instance and proxy it
        proxy = proxy_class(**self.init_kwargs)
        proxy.bind(field_name, parent)
        self._proxy = proxy
        return None

    def to_internal_value(self, data):
        pass

    def to_representation(self, value):
        pass


class WritableSerializerMethodField(serializers.SerializerMethodField):
    def __init__(self, **kwargs):
        self.write_field = kwargs.pop("write_field")
        super().__init__(**kwargs)
        self.read_only = False

    def to_internal_value(self, data):
        return {self.field_name: self.write_field.to_internal_value(data)}


class PrivacySettingFieldMixin:
    def __init__(self, **kwargs):
        self.privacy_field = kwargs.pop("privacy_field", "")
        self.default_value = kwargs.pop("default_value", None)
        assert self.privacy_field in [
            f.name for f in PrivacySettings._meta.get_fields()
        ]
        super().__init__(**kwargs)

    def _get_user(self, value):
        if isinstance(value, ProjectUser):
            return value
        user_data = getattr(self.parent, "instance", None) or getattr(
            self.parent, "queryset", None
        )
        if (
            user_data
            and isinstance(user_data, QuerySet)
            and user_data.model == ProjectUser
            and user_data.count() == 1
        ):
            return user_data.get()
        if (
            user_data
            and isinstance(user_data, QuerySet)
            and user_data.model == ProjectUser
            and self.source_attrs
        ):
            try:
                return user_data.filter(**{self.source_attrs[0]: value}).first()
            except TypeError:  # filter raises a TypeError if queryset has been sliced
                user_data = list(user_data)
        if user_data and isinstance(user_data, ProjectUser):
            return user_data
        if user_data and isinstance(user_data, list) and len(user_data) == 1:
            return user_data[0]
        if user_data and isinstance(user_data, list) and self.source_attrs:
            return [
                user
                for user in user_data
                if getattr(user, self.source_attrs[0]) == value
            ][0]
        if self.source_attrs:
            with suppress(
                ProjectUser.MultipleObjectsReturned, ProjectUser.DoesNotExist
            ):
                return ProjectUser.objects.get(**{self.source_attrs[0]: value})
        return None

    def _check_privacy_settings(self, value):
        instance = self._get_user(value)
        assert isinstance(instance, ProjectUser)
        request = self.context.get("request")
        assert request is not None

        if instance == request.user or request.user.groups.contains(
            get_superadmins_group()
        ):
            return True
        settings, _ = PrivacySettings.objects.get_or_create(user=instance)
        match getattr(settings, self.privacy_field):
            case PrivacySettings.PrivacyChoices.PUBLIC:
                return True
            case PrivacySettings.PrivacyChoices.ORGANIZATION:
                return instance.groups.filter(
                    organizations__isnull=False,
                    organizations__in=request.user.get_related_organizations(),
                ).exists()
            case PrivacySettings.PrivacyChoices.HIDE:
                if not request.user.is_authenticated or not isinstance(
                    request.user, ProjectUser
                ):
                    return False
                return Group.objects.filter(
                    organizations__isnull=False,
                    organizations__in=instance.get_related_organizations(),
                    name__contains="admins",
                    users=request.user,
                ).exists()
        return False

    def to_representation(self, value):
        if self._check_privacy_settings(value):
            return super().to_representation(value)
        return self.default_value


class PrivacySettingProtectedCharField(PrivacySettingFieldMixin, serializers.CharField):
    pass


class PrivacySettingProtectedEmailField(
    PrivacySettingFieldMixin, serializers.EmailField
):
    pass


class PrivacySettingProtectedMethodField(
    PrivacySettingFieldMixin, serializers.SerializerMethodField
):
    pass


@extend_schema_field(OpenApiTypes.NONE)
class HiddenSlugRelatedField(serializers.SlugRelatedField):
    pass


@extend_schema_field(OpenApiTypes.NONE)
class HiddenPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    pass
