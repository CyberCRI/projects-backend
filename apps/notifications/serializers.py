from rest_framework import serializers

from apps.accounts.serializers import UserLightSerializer
from apps.commons.serializers import TranslatedModelSerializer
from apps.invitations.serializers import InvitationSerializer
from apps.projects.serializers import ProjectSuperLightSerializer

from .models import Notification, NotificationSettings


class EmailReportSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    reported_by = serializers.EmailField(required=True)
    url = serializers.URLField(required=True)


class ContactSerializer(serializers.Serializer):
    subject = serializers.CharField(required=True)
    content = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)


class NotificationsSerializer(TranslatedModelSerializer):
    sender = UserLightSerializer(read_only=True)
    project = ProjectSuperLightSerializer(read_only=True)
    invitation = InvitationSerializer(read_only=True)

    class Meta:
        model = Notification
        read_only_fields = [
            "id",
            "sender",
            "project",
            "type",
            "context",
            "created",
            "invitation",
        ]
        fields = read_only_fields + ["is_viewed"]


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = (
            "notify_added_to_project",
            "announcement_published",
            "followed_project_has_been_edited",
            "project_has_been_commented",
            "project_has_been_edited",
            "project_ready_for_review",
            "project_has_been_reviewed",
            "announcement_has_new_application",
            "comment_received_a_response",
        )
