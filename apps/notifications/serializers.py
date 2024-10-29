from rest_framework import serializers

from apps.accounts.serializers import UserLighterSerializer
from apps.commons.serializers import TranslatedModelSerializer
from apps.invitations.serializers import InvitationSerializer
from apps.organizations.models import Organization
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
    sender = UserLighterSerializer(read_only=True)
    project = ProjectSuperLightSerializer(read_only=True)
    invitation = InvitationSerializer(read_only=True)
    organization = serializers.SlugRelatedField(
        slug_field="name", queryset=Organization.objects.all()
    )

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
            "organization",
            "count",
        ]
        fields = read_only_fields + ["is_viewed"]


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        read_only_fields = ["id"]
        fields = read_only_fields + [
            "notify_added_to_project",
            "announcement_published",
            "announcement_has_new_application",
            "followed_project_has_been_edited",
            "project_has_been_commented",
            "project_has_been_edited",
            "project_ready_for_review",
            "project_has_been_reviewed",
            "project_has_new_private_message",
            "comment_received_a_response",
            "organization_has_new_access_request",
            "invitation_link_will_expire",
            "new_instruction",
        ]
