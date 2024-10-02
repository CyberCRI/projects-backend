from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.commons.fields import UserMultipleIdRelatedField
from apps.commons.serializers import TranslatedModelSerializer

from .exceptions import UpdateWrongTypeTagClassificationError, UpdateWrongTypeTagError
from .models import Skill, Tag, TagClassification


class TagClassificationSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(read_only=True, slug_field="code")
    is_owned = serializers.SerializerMethodField()
    is_enabled = serializers.SerializerMethodField()

    def get_is_owned(self, tag_classification: TagClassification) -> bool:
        organization = self.context.get("organization", None)
        return organization and tag_classification.organization == organization

    def get_is_enabled(self, tag_classification: TagClassification) -> bool:
        organization = self.context.get("organization", None)
        return (
            organization
            and tag_classification in organization.enabled_tag_classifications
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
