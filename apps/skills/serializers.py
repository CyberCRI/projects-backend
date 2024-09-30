from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import ProjectUser
from apps.commons.fields import UserMultipleIdRelatedField
from apps.commons.serializers import TranslatedModelSerializer
from apps.skills.utils import update_or_create_wikipedia_tag

from .models import Skill, Tag


class TagSerializer(TranslatedModelSerializer):
    mentors_count = serializers.IntegerField(required=False, read_only=True)
    mentorees_count = serializers.IntegerField(required=False, read_only=True)

    def validate_type(self, value: str) -> str:
        if value != Tag.TagType.CUSTOM:
            raise serializers.ValidationError("Only custom tags can be created.")
        return value

    def validate_secondary_type(self, value: str) -> str:
        if value:
            raise serializers.ValidationError(
                "Secondary type is not allowed for custom tags."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        if self.instance and self.instance.type != Tag.TagType.CUSTOM:
            raise serializers.ValidationError("Only custom tags can be updated.")
        return super().validate(attrs)

    class Meta:
        model = Tag
        read_only_fields = [
            "type",
            "secondary_type" "mentors_count",
            "mentorees_count",
        ]
        fields = read_only_fields + [
            "id",
            "title",
            "description",
        ]


@extend_schema_field(OpenApiTypes.STR)
class TagRelatedField(serializers.RelatedField):
    def get_queryset(self) -> QuerySet:
        return Tag.objects.all()

    def to_representation(self, instance: Tag) -> dict:
        return TagSerializer(instance).data

    def to_internal_value(self, tag_id: int) -> Tag:
        tag = Tag.objects.get(id=tag_id)
        if tag.type == Tag.TagType.WIKIPEDIA:
            return update_or_create_wikipedia_tag(tag.external_id)
        return tag


class SkillLightSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)

    class Meta:
        model = Skill
        read_only_fields = [
            "id",
            "wikipedia_tag",
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
    user = UserMultipleIdRelatedField(queryset=ProjectUser.objects.all())
    tag = TagRelatedField()

    class Meta:
        model = Skill
        fields = [
            "id",
            "user",
            "wikipedia_tag",
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
