from typing import List

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.commons.fields import HiddenPrimaryKeyRelatedField, UserMultipleIdRelatedField
from apps.commons.serializers import TranslatedModelSerializer

from .exceptions import (
    TagFromWrongOrganizationError,
    UpdateWrongTypeTagClassificationError,
    UpdateWrongTypeTagError,
)
from .models import Skill, Tag, TagClassification


class TagClassificationLightSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(read_only=True, slug_field="code")

    class Meta:
        model = TagClassification
        read_only_fields = [
            "id",
            "type",
            "slug",
            "organization",
        ]
        fields = read_only_fields


class TagClassificationSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(read_only=True, slug_field="code")
    is_owned = serializers.SerializerMethodField()
    is_enabled = serializers.SerializerMethodField()

    def get_is_owned(self, tag_classification: TagClassification) -> bool:
        organization = self.context.get("current_organization", None)
        return organization and tag_classification.organization == organization

    def get_is_enabled(self, tag_classification: TagClassification) -> bool:
        organization = self.context.get("current_organization", None)
        return (
            organization
            and tag_classification in organization.enabled_tag_classifications.all()
        )

    class Meta:
        model = TagClassification
        read_only_fields = [
            "id",
            "type",
            "slug",
            "organization",
            "is_owned",
            "is_enabled",
        ]
        fields = read_only_fields + [
            "title",
            "description",
            "is_public",
        ]

    def validate(self, attrs: dict) -> dict:
        if self.instance and self.instance.type != Tag.TagType.CUSTOM:
            raise UpdateWrongTypeTagClassificationError
        return super().validate(attrs)


@extend_schema_field(OpenApiTypes.STR)
class TagClassificationMultipleIdRelatedField(serializers.RelatedField):
    """
    A read-write field that allows multiple ids to be used to represent a tag classification.

    Possible ids are:
        - id
        - slug
    """

    default_error_messages = {
        "required": _("This field is required."),
        "does_not_exist": _(
            'Invalid id "{tag_classification_id}" - object does not exist.'
        ),
        "incorrect_type": _(
            "Incorrect type. Expected str value, received {data_type}."
        ),
    }

    def __init__(self, **kwargs):
        self.tag_classification_lookup = kwargs.pop("tag_classification_lookup", "")
        super().__init__(**kwargs)

    def get_queryset(self) -> QuerySet:
        return TagClassification.objects.all()

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            lookup_field = TagClassification.get_id_field_name(data)
            if self.tag_classification_lookup:
                lookup_field = f"{self.tag_classification_lookup}__{lookup_field}"
            return get_object_or_404(queryset, **{lookup_field: data})
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(data).__name__)

    def to_representation(self, value):
        return TagClassificationLightSerializer(value).data


class TagClassificationAddTagsSerializer(serializers.Serializer):
    tag_classification = HiddenPrimaryKeyRelatedField(
        write_only=True, queryset=TagClassification.objects.all()
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Tag.objects.all()
    )

    def validate_tags(self, tags: List[Tag]) -> List[Tag]:
        organization = self.context.get("current_organization", None)
        if organization and any(
            (tag.organization and tag.organization != organization) for tag in tags
        ):
            raise TagFromWrongOrganizationError
        return tags

    def create(self, validated_data):
        tag_classification = validated_data["tag_classification"]
        tags = validated_data.get("tags", [])
        tag_classification.tags.add(*tags)
        return tag_classification


class TagClassificationRemoveTagsSerializer(serializers.Serializer):
    tag_classification = HiddenPrimaryKeyRelatedField(
        write_only=True, queryset=TagClassification.objects.all()
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Tag.objects.all()
    )

    def create(self, validated_data):
        tag_classification = validated_data["tag_classification"]
        tags = validated_data.get("tags", [])
        tag_classification.tags.remove(*tags)
        return tag_classification


class TagSerializer(TranslatedModelSerializer):
    mentors_count = serializers.IntegerField(required=False, read_only=True)
    mentorees_count = serializers.IntegerField(required=False, read_only=True)

    class Meta:
        model = Tag
        read_only_fields = [
            "id",
            "type",
            "secondary_type",
            "mentors_count",
            "mentorees_count",
        ]
        fields = read_only_fields + [
            "title",
            "description",
        ]

    def validate(self, attrs: dict) -> dict:
        if self.instance and self.instance.type != Tag.TagType.CUSTOM:
            raise UpdateWrongTypeTagError
        return super().validate(attrs)


@extend_schema_field(OpenApiTypes.STR)
class TagRelatedField(serializers.RelatedField):
    def get_queryset(self) -> QuerySet:
        return Tag.objects.all()

    def to_representation(self, instance: Tag) -> dict:
        return TagSerializer(instance).data

    def to_internal_value(self, tag_id: int) -> Tag:
        return Tag.objects.get(id=tag_id)


class SkillLightSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)

    class Meta:
        model = Skill
        read_only_fields = [
            "id",
            "tag",
            "level",
            "level_to_reach",
            "category",
            "type",
            "can_mentor",
            "needs_mentor",
            "comment",
        ]
        fields = read_only_fields


class SkillSerializer(serializers.ModelSerializer):
    user = UserMultipleIdRelatedField(read_only=True)
    tag = TagRelatedField()

    class Meta:
        model = Skill
        fields = [
            "id",
            "user",
            "tag",
            "level",
            "level_to_reach",
            "category",
            "type",
            "can_mentor",
            "needs_mentor",
            "comment",
        ]


class MentorshipContactSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    reply_to = serializers.EmailField()
