from rest_framework import serializers

from apps.accounts.models import PeopleGroup
from apps.announcements.serializers import AnnouncementSerializer
from apps.commons.serializers import OrganizationRelatedSerializer
from apps.files.models import Image
from apps.files.serializers import ImageSerializer
from apps.organizations.models import Organization
from apps.projects.serializers import ProjectLightSerializer

from .exceptions import NewsPeopleGroupOrganizationError
from .models import News, Newsfeed


class NewsSerializer(OrganizationRelatedSerializer, serializers.ModelSerializer):
    header_image = ImageSerializer(read_only=True)
    organization = serializers.SlugRelatedField(
        slug_field="code", queryset=Organization.objects.all()
    )
    people_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=PeopleGroup.objects.all()
    )

    # write_only
    header_image_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Image.objects.all(),
        source="header_image",
        required=False,
    )

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "content",
            "publication_date",
            "header_image",
            "organization",
            "people_groups",
            "language",
            "created_at",
            "updated_at",
            # write_only
            "header_image_id",
        ]

    def validate_people_groups(self, value):
        for group in value:
            if group.organization.code != self.context.get("organization_code"):
                raise NewsPeopleGroupOrganizationError
        return value


class NewsfeedSerializer(serializers.ModelSerializer):
    project = ProjectLightSerializer(many=False, read_only=True)
    announcement = AnnouncementSerializer(many=False, read_only=True)
    type = serializers.CharField(max_length=50)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Newsfeed
        read_only_fields = ["id"]
        fields = read_only_fields + [
            "project",
            "announcement",
            "type",
            "updated_at",
        ]
