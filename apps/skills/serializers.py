from typing import List

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import empty

from apps.commons.fields import HiddenPrimaryKeyRelatedField, UserMultipleIdRelatedField
from apps.commons.serializers import (
    LazySerializer,
    StringsImagesSerializer,
    TranslatedModelSerializer,
)
from apps.commons.utils import process_text
from services.translator.serializers import AutoTranslatedModelSerializer

from .exceptions import (
    TagDescriptionTooLongError,
    TagFromWrongOrganizationError,
    TagTitleTooLongError,
    UpdateWrongTypeTagClassificationError,
    UpdateWrongTypeTagError,
)
from .models import Mentoring, Skill, Tag, TagClassification


class TagClassificationLightSerializer(
    AutoTranslatedModelSerializer, serializers.ModelSerializer
):
    organization = serializers.SlugRelatedField(read_only=True, slug_field="code")

    class Meta:
        model = TagClassification
        read_only_fields = [
            "id",
            "type",
            "slug",
            "organization",
            "title",
            "description",
        ]
        fields = read_only_fields


class TagClassificationSerializer(
    StringsImagesSerializer, AutoTranslatedModelSerializer, serializers.ModelSerializer
):
    string_images_forbid_fields: List[str] = ["title", "description"]

    organization = serializers.SlugRelatedField(read_only=True, slug_field="code")
    is_owned = serializers.SerializerMethodField()
    is_enabled_for_projects = serializers.SerializerMethodField()
    is_enabled_for_skills = serializers.SerializerMethodField()

    def get_is_owned(self, tag_classification: TagClassification) -> bool:
        organization = self.context.get("current_organization")
        return organization and tag_classification.organization == organization

    def get_is_enabled_for_projects(
        self, tag_classification: TagClassification
    ) -> bool:
        organization = self.context.get("current_organization")
        return (
            organization
            and tag_classification
            in organization.enabled_projects_tag_classifications.all()
        )

    def get_is_enabled_for_skills(self, tag_classification: TagClassification) -> bool:
        organization = self.context.get("current_organization")
        return (
            organization
            and tag_classification
            in organization.enabled_skills_tag_classifications.all()
        )

    class Meta:
        model = TagClassification
        read_only_fields = [
            "id",
            "type",
            "slug",
            "organization",
            "is_owned",
            "is_enabled_for_projects",
            "is_enabled_for_skills",
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
        return TagClassification.objects.all().select_related("organization")

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
        organization = self.context.get("current_organization")
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
    highlight = serializers.JSONField(required=False, read_only=True)

    class Meta:
        model = Tag
        read_only_fields = [
            "id",
            "type",
            "secondary_type",
            "mentors_count",
            "mentorees_count",
            "highlight",
        ]
        fields = read_only_fields + [
            "title",
            "description",
        ]

    def validate_title(self, title: str) -> str:
        """
        We validate the title length here because we use a larger limit for the
        model field to allow for external tags over which we have no control.
        """
        if len(title) > 50:
            raise TagTitleTooLongError
        return title

    def validate_description(self, description: str) -> str:
        """
        We validate the description length here because we use a larger limit for the
        model field to allow for external tags over which we have no control.
        """
        if len(description) > 500:
            raise TagDescriptionTooLongError
        return description

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


class MentoringContactSerializer(serializers.Serializer):
    content = serializers.CharField()
    reply_to = serializers.EmailField(required=False, allow_null=True)

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance=instance, data=data, **kwargs)
        if hasattr(self, "initial_data"):
            reply_to = self.initial_data.get("reply_to")
            if not reply_to and "request" in self.context:
                context = self.context
                user = context["request"].user
                self.initial_data["reply_to"] = user.email

    def validate_content(self, content: str) -> str:
        content, _ = process_text(content, forbid_images=True)
        return content


class MentoringResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Mentoring.MentoringStatus.choices, required=True
    )
    content = serializers.CharField()
    reply_to = serializers.EmailField(required=False, allow_null=True)

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance=instance, data=data, **kwargs)
        if hasattr(self, "initial_data"):
            reply_to = self.initial_data.get("reply_to")
            if not reply_to and "request" in self.context:
                context = self.context
                user = context["request"].user
                self.initial_data["reply_to"] = user.email

    def validate_content(self, content: str) -> str:
        content, _ = process_text(content, forbid_images=True)
        return content


class MentoringSerializer(serializers.ModelSerializer):
    mentor = LazySerializer(
        "apps.accounts.serializers.UserLighterSerializer", read_only=True
    )
    mentoree = LazySerializer(
        "apps.accounts.serializers.UserLighterSerializer", read_only=True
    )
    skill = SkillLightSerializer(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Mentoring
        read_only_fields = [
            "id",
            "mentor",
            "mentoree",
            "skill",
            "status",
            "created_by",
            "created_at",
        ]
        fields = read_only_fields
