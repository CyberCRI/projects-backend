from rest_framework import serializers

from apps.announcements.serializers import AnnouncementSerializer
from apps.newsfeed.models import Newsfeed
from apps.projects.serializers import ProjectLightSerializer


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
