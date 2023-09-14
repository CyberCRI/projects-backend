from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import ProjectUser
from apps.commons.db.abc import ProjectRelated
from apps.emailing.utils import render_message, send_email
from apps.feedbacks.models import Follow
from apps.projects.models import Project

from .models import Notification


class NotificationTaskManager:
    """Manage the notification tasks."""

    member_setting_name: str
    notification_type: Notification.Types.choices
    template_dir: str
    follower_setting_name: str = "followed_project_has_been_edited"
    notify_followers: bool = False
    send_immediately: bool = False
    merge: bool = True

    def __init__(
        self,
        sender: Optional[ProjectUser],
        item: Union[Project, ProjectRelated],
        **kwargs,
    ):
        self.sender = sender
        self.item = item
        self.project = item if isinstance(item, Project) else item.project
        self.base_context = kwargs
        self.template_context = {
            "project": self.project,
            "by": sender,
            "item": item,
            **kwargs,
        }

    def get_recipients(self) -> List[ProjectUser]:
        """
        Return the recipients of the notification.
        """
        raise NotImplementedError

    def get_translated_reminder(self, language, **context):
        """
        Return the reminder message in the given language.
        """
        reminder, _ = render_message(
            f"{self.template_dir}/reminder", language, **context
        )
        return reminder

    def send_email_to_recipient(self, recipient: ProjectUser, **context) -> None:
        """
        Send the email to the receiver.
        """
        recipient_context = self.format_context_for_template(
            {"recipient": recipient, **context}, recipient.language
        )
        subject, _ = render_message(
            f"{self.template_dir}/object", recipient.language, **recipient_context
        )
        text, html = render_message(
            f"{self.template_dir}/mail", recipient.language, **recipient_context
        )
        send_email(subject, text, [recipient.email], html_content=html)

    def format_context_for_template(
        self, context: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        """
        Return the context to be passed to the templates.
        """
        return context

    @staticmethod
    def merge_context_lists(
        current_value: List[Any], new_value: List[Any]
    ) -> Dict[str, Any]:
        """
        Return the context to be passed to the front.
        """
        if (
            len(new_value) > 0
            and all(isinstance(d, dict) for d in new_value)
            and all("keycloak_id" in d for d in new_value)
        ):
            return list(
                {v["keycloak_id"]: v for v in current_value + new_value}.values()
            )
        if (
            len(new_value) > 0
            and all(isinstance(d, dict) for d in new_value)
            and all("id" in d for d in new_value)
        ):
            return list({v["id"]: v for v in current_value + new_value}.values())
        return list(set(current_value + new_value))

    def recipient_must_receive(self, recipient: ProjectUser) -> bool:
        """
        Return True if the notification should be sent to the recipient.
        """
        to_send = getattr(
            recipient.notification_settings, self.member_setting_name, False
        )
        if self.notify_followers:
            to_send &= self.project.get_all_members().filter(id=recipient.id).exists()
            to_send |= (
                getattr(
                    recipient.notification_settings, self.follower_setting_name, False
                )
                and Follow.objects.filter(
                    project=self.project, follower=recipient
                ).exists()
            )
        return to_send

    def update_or_create_notification_for_recipient(
        self, recipient: ProjectUser
    ) -> Notification:
        lookup = {
            "type": self.notification_type,
            "sender": self.sender,
            "receiver": recipient,
            "project": self.project,
            "to_send": self.recipient_must_receive(recipient)
            and not self.send_immediately,
        }
        defaults = {
            f"reminder_message_{lang}": self.get_translated_reminder(
                lang,
                count=1,
                **self.format_context_for_template(self.template_context, lang),
            )
            for lang in settings.REQUIRED_LANGUAGES
        }
        if self.send_immediately:
            lookup["is_viewed"] = False
        else:
            defaults["is_viewed"] = False
        if self.merge:
            notification, created = Notification.objects.update_or_create(
                defaults, **lookup
            )
        else:
            notification = Notification.objects.create(**defaults, **lookup)
            created = True
        context = self.base_context
        if not created:
            context = {
                key: value
                if not isinstance(value, list)
                else self.merge_context_lists(notification.context.get(key, []), value)
                for key, value in context.items()
            }
            notification.count += 1
            for lang in settings.REQUIRED_LANGUAGES:
                setattr(
                    notification,
                    f"reminder_message_{lang}",
                    self.get_translated_reminder(
                        lang,
                        count=notification.count,
                        **self.format_context_for_template(
                            {**self.template_context, **context}, lang
                        ),
                    ),
                )
        notification.context = context
        notification.save()
        context = {"count": notification.count, **self.template_context, **context}
        return notification, context

    def create_and_send_notifications(self) -> None:
        """
        Create and send notifications to the recipients.
        """
        for recipient in self.get_recipients():
            _, context = self.update_or_create_notification_for_recipient(recipient)
            if self.recipient_must_receive(recipient) and self.send_immediately:
                self.send_email_to_recipient(recipient, **context)


class ProjectEditedNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.PROJECT_UPDATED
    template_dir = "notifications/project_edited"
    notify_followers = True

    def get_recipients(self) -> List[ProjectUser]:
        return (
            (
                self.project.get_all_members()
                | ProjectUser.objects.filter(follows__project=self.project)
            )
            .exclude(id=self.sender.id)
            .distinct()
        )

    def format_context_for_template(
        self, context: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        join_word = _(" and ")
        updated_fields = context.get("updated_fields", [])
        with translation.override(language):
            updated_fields = [translation.gettext(_(field)) for field in updated_fields]
            updated_fields = join_word.join(
                [", ".join(updated_fields[:-1]), updated_fields[-1]]
                if len(updated_fields) > 2
                else updated_fields
            )
        return {**context, "updated_fields": updated_fields}


class BlogEntryNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.BLOG_ENTRY
    template_dir = "notifications/new_blogentry"
    notify_followers = True

    def get_recipients(self) -> List[ProjectUser]:
        return (
            (
                self.project.get_all_members()
                | ProjectUser.objects.filter(follows__project=self.project)
            )
            .exclude(id=self.sender.id)
            .distinct()
        )


class AnnouncementNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.ANNOUNCEMENT
    template_dir = "notifications/new_announcement"
    notify_followers = True

    def get_recipients(self) -> List[ProjectUser]:
        return (
            (
                self.project.get_all_members()
                | ProjectUser.objects.filter(follows__project=self.project)
            )
            .exclude(id=self.sender.id)
            .distinct()
        )


class ApplicationNotificationManager(NotificationTaskManager):
    member_setting_name = "announcement_has_new_application"
    notification_type = Notification.Types.APPLICATION
    template_dir = "notifications/new_application"
    notify_followers = True
    send_immediately = True
    merge = False

    def get_recipients(self) -> List[ProjectUser]:
        return self.project.get_all_members()

    def format_context_for_template(
        self, context: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        return {"announcement_title": self.item.title, **context}


class CommentNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_commented"
    notification_type = Notification.Types.COMMENT
    template_dir = "notifications/new_comment"
    send_immediately = True

    def get_recipients(self) -> List[ProjectUser]:
        recipients = self.project.get_all_members().exclude(id=self.sender.id)
        if self.item.reply_on is not None:
            return recipients.exclude(id=self.item.reply_on.author.id).distinct()
        return recipients.distinct()


class FollowerCommentNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_commented"
    notification_type = Notification.Types.COMMENT
    template_dir = "notifications/new_comment"
    notify_followers = True

    def get_recipients(self) -> List[ProjectUser]:
        recipients = ProjectUser.objects.filter(follows__project=self.project).exclude(
            id=self.sender.id
        )
        if self.item.reply_on is not None:
            return recipients.exclude(id=self.item.reply_on.author.id).distinct()
        return recipients.distinct()


class CommentReplyNotificationManager(NotificationTaskManager):
    member_setting_name = "comment_received_a_response"
    notification_type = Notification.Types.REPLY
    template_dir = "notifications/new_reply"
    send_immediately = True

    def get_recipients(self) -> List[ProjectUser]:
        if self.item.reply_on is not None:
            return [self.item.reply_on.author]
        return []


class ReadyForReviewNotificationManager(NotificationTaskManager):
    member_setting_name = "project_ready_for_review"
    notification_type = Notification.Types.READY_FOR_REVIEW
    template_dir = "notifications/project_ready_for_review"
    send_immediately = True

    def get_recipients(self) -> List[ProjectUser]:
        return self.project.reviewers.all().exclude(id=self.sender.id).distinct()


class ReviewNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_reviewed"
    notification_type = Notification.Types.REVIEW
    template_dir = "notifications/new_review"
    notify_followers = True
    send_immediately = True

    def get_recipients(self) -> List[ProjectUser]:
        return (
            (
                self.project.get_all_members()
                | ProjectUser.objects.filter(follows__project=self.project)
            )
            .exclude(id=self.sender.id)
            .distinct()
        )


class DeleteMembersNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.MEMBER_REMOVED
    template_dir = "notifications/member_removed_other"

    def get_recipients(self) -> List[ProjectUser]:
        return self.project.get_all_members().exclude(id=self.sender.id).distinct()


class DeleteGroupMembersNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.GROUP_MEMBER_REMOVED
    template_dir = "notifications/group_member_removed_other"

    def get_recipients(self) -> List[ProjectUser]:
        return self.project.get_all_members().exclude(id=self.sender.id).distinct()


class UpdateMembersNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.MEMBER_UPDATED
    template_dir = "notifications/member_updated_other"

    def get_recipients(self) -> List[ProjectUser]:
        keycloak_ids = [
            self.sender.keycloak_id,
            *[m["keycloak_id"] for m in self.base_context["modified_members"]],
        ]
        return (
            self.project.get_all_members()
            .exclude(keycloak_id__in=keycloak_ids)
            .distinct()
        )

    def format_context_for_template(
        self, context: Dict[str, Any], language: str
    ) -> Dict[str, Any]:

        modified_members = context.get("modified_members", [])
        with translation.override(language):
            modified_members = [
                {**member, "role": translation.gettext(_(member["role"]))}
                for member in modified_members
            ]
        return {**context, "modified_members": modified_members}


class UpdatedMemberNotificationManager(NotificationTaskManager):
    member_setting_name = "notify_added_to_project"
    notification_type = Notification.Types.MEMBER_UPDATED_SELF
    template_dir = "notifications/member_updated_self"
    send_immediately = (True,)

    def get_recipients(self) -> List[ProjectUser]:
        keycloak_ids = [m["keycloak_id"] for m in self.base_context["modified_members"]]
        return ProjectUser.objects.filter(keycloak_id__in=keycloak_ids).exclude(
            id=self.sender.id
        )

    def format_context_for_template(
        self, context: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        modified_members = context.get("modified_members", [{}])
        with translation.override(language):
            role = translation.gettext(_(modified_members[0].get("role")))
        return {**context, "role": role}


class AddMembersNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.MEMBER_ADDED
    template_dir = "notifications/member_added_other"

    def get_recipients(self) -> List[ProjectUser]:
        keycloak_ids = [
            self.sender.keycloak_id,
            *[m["keycloak_id"] for m in self.base_context["new_members"]],
        ]
        return (
            self.project.get_all_members()
            .exclude(keycloak_id__in=keycloak_ids)
            .distinct()
        )


class AddMemberNotificationManager(NotificationTaskManager):
    member_setting_name = "notify_added_to_project"
    notification_type = Notification.Types.MEMBER_ADDED_SELF
    template_dir = "notifications/member_added_self"
    send_immediately = (True,)

    def get_recipients(self) -> List[ProjectUser]:
        keycloak_ids = [m["keycloak_id"] for m in self.base_context["new_members"]]
        return ProjectUser.objects.filter(keycloak_id__in=keycloak_ids).exclude(
            id=self.sender.id
        )


class AddGroupMembersNotificationManager(NotificationTaskManager):
    member_setting_name = "project_has_been_edited"
    notification_type = Notification.Types.GROUP_MEMBER_ADDED
    template_dir = "notifications/group_member_added_other"

    def get_recipients(self) -> List[ProjectUser]:
        keycloak_ids = self.base_context["new_members"] + [
            self.sender.keycloak_id,
        ]

        return (
            self.project.get_all_members()
            .exclude(keycloak_id__in=keycloak_ids)
            .distinct()
        )


class AddGroupMemberNotificationManager(NotificationTaskManager):
    member_setting_name = "notify_added_to_project"
    notification_type = Notification.Types.GROUP_MEMBER_ADDED_SELF
    template_dir = "notifications/group_member_added_self"
    send_immediately = True

    def get_recipients(self) -> List[ProjectUser]:
        return ProjectUser.objects.filter(
            keycloak_id__in=self.base_context["new_members"]
        ).exclude(id=self.sender.id)
