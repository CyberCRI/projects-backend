from typing import TYPE_CHECKING

from django.db import models

from apps.commons.db.abc import HasOwner

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Notification(models.Model, HasOwner):
    class Types(models.TextChoices):
        """Different types of notifications."""

        COMMENT = "comment"
        REPLY = "reply"
        REVIEW = "review"
        READY_FOR_REVIEW = "ready_for_review"
        PROJECT_UPDATED = "project_updated"
        MEMBER_ADDED_SELF = "member_added_self"
        GROUP_MEMBER_ADDED_SELF = "group_member_added_self"
        MEMBER_UPDATED_SELF = "member_updated_self"
        MEMBER_ADDED = "member_added"
        MEMBER_UPDATED = "member_updated"
        MEMBER_REMOVED = "member_removed"
        GROUP_MEMBER_REMOVED = "group_member_removed"
        GROUP_MEMBER_ADDED = "group_member_added"
        ANNOUNCEMENT = "announcement"
        APPLICATION = "application"
        BLOG_ENTRY = "blog_entry"
        INVITATION_TODAY_REMINDER = "invitation_today_reminder"
        INVITATION_WEEK_REMINDER = "invitation_week_reminder"

    class ExpirationTypes(models.TextChoices):
        """Different dates of expiration."""

        DEFAULT = ""
        WEEK = "week"
        TODAY = "today"

    sender = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="notifications_sent",
        null=True,
    )
    receiver = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="notifications_received",
    )
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, null=True)
    invitation = models.ForeignKey(
        "invitations.Invitation", on_delete=models.CASCADE, null=True
    )
    is_viewed = models.BooleanField(default=False)
    to_send = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)
    reminder_message = models.CharField(max_length=255, blank=True, default="")
    type = models.CharField(
        max_length=30, choices=Types.choices, default=Types.PROJECT_UPDATED.value
    )
    context = models.JSONField(default=dict)
    count = models.IntegerField(default=1)

    def is_owned_by(self, user: "ProjectUser") -> bool:
        return self.receiver == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.receiver


class NotificationSettings(models.Model, HasOwner):
    user = models.OneToOneField(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        to_field="keycloak_id",
        related_name="notification_settings",
    )
    notify_added_to_project = models.BooleanField(default=True)
    announcement_published = models.BooleanField(default=True)
    announcement_has_new_application = models.BooleanField(default=True)
    followed_project_has_been_edited = models.BooleanField(default=True)
    project_has_been_commented = models.BooleanField(default=True)
    project_has_been_edited = models.BooleanField(default=True)
    project_ready_for_review = models.BooleanField(default=True)
    project_has_been_reviewed = models.BooleanField(default=True)
    comment_received_a_response = models.BooleanField(default=True)

    def is_owned_by(self, user: "ProjectUser") -> bool:
        return self.user == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.user
