from rest_framework import serializers

from apps.commons.serializers import TranslatedModelSerializer
from apps.files.serializers import ImageSerializer
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.skills.models import Tag
from apps.skills.serializers import TagSerializer


class StatsOrganizationSerializer(serializers.ModelSerializer):
    logo_image = ImageSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    project_count = serializers.IntegerField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "background_color",
            "code",
            "language",
            "name",
            "website_url",
            "created_at",
            "updated_at",
            "logo_image",
            "tags",
            "project_count",
        ]


class ProjectBySDG(serializers.Serializer):
    sdg = serializers.IntegerField()
    project_count = serializers.IntegerField()


class ProjectByMonth(serializers.Serializer):
    month = serializers.DateField()
    created_count = serializers.IntegerField()
    updated_count = serializers.IntegerField()


class TagProjectSerializer(TranslatedModelSerializer):
    projects = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Project.objects.all()
    )
    project_count = serializers.IntegerField()

    class Meta:
        model = Tag
        fields = ["id", "title", "projects", "project_count"]


class StatsSerializer(serializers.Serializer):
    by_sdg = ProjectBySDG(many=True)
    by_month = ProjectByMonth(many=True)
    top_tags = TagProjectSerializer(many=True)
    total = serializers.IntegerField()
