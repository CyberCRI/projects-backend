from datetime import date, timedelta
from typing import Any, Dict, Set

from babel.dates import format_date
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.models import Announcement
from apps.emailing.utils import render_message, send_email
from apps.feedbacks.models import Comment, Review
from apps.invitations.models import AccessRequest, Invitation
from apps.newsfeed.models import Instruction
from apps.organizations.models import Organization
from apps.projects.models import BlogEntry, Project
from projects.celery import app

from .models import Notification
from .utils import (
    AddGroupMemberNotificationManager,
    AddGroupMembersNotificationManager,
    AddMemberNotificationManager,
    AddMembersNotificationManager,
    AnnouncementNotificationManager,
    ApplicationNotificationManager,
    BlogEntryNotificationManager,
    CommentNotificationManager,
    CommentReplyNotificationManager,
    DeleteGroupMembersNotificationManager,
    DeleteMembersNotificationManager,
    FollowerCommentNotificationManager,
    InvitationExpiresInOneWeekNotificationManager,
    InvitationExpiresTodayNotificationManager,
    NewAccessRequestNotificationManager,
    NewInstructionNotificationManager,
    PendingAccessRequestsNotificationManager,
    ProjectEditedNotificationManager,
    ReadyForReviewNotificationManager,
    ReviewNotificationManager,
    UpdatedMemberNotificationManager,
    UpdateMembersNotificationManager,
)


@app.task
def notify_member_added(project_pk: str, user_pk: int, by_pk: int, role: str):
    """Notify that members has been added to a project.

    New members are notified they have been added, while previous members are
    notified of all the newly added members.
    """
    return _notify_member_added(project_pk, user_pk, by_pk, role)


@app.task
def notify_group_as_member_added(project_pk: str, group_id: int, by_pk: int):
    """Notify that a people group has been added to a project as member.

    New members are notified they have been added, while previous members are
    notified of all the newly added members.
    """
    return _notify_group_as_member_added(project_pk, group_id, by_pk)


@app.task
def notify_member_updated(project_pk: str, user_pk: int, by_pk: int, role: str):
    """Notify that members of a project has been updated.

    Updated members are notified of their new role, while other members are
    notified about all the updated members.
    """
    return _notify_member_updated(project_pk, user_pk, by_pk, role)


@app.task
def notify_member_deleted(project_pk: str, user_pk: int, by_pk: int):
    """Notify that members has been deleted from a project.

    Deleted members are notified they have been deleted, while other members are
    notified of all the deleted members.
    """
    return _notify_member_deleted(project_pk, user_pk, by_pk)


@app.task
def notify_group_member_deleted(project_pk: str, people_group_pk: int, by_pk: int):
    """Notify that a group has been deleted from the members of a project.

    Deleted members are notified they have been deleted, while other members are
    notified of all the deleted members.
    """
    return _notify_group_member_deleted(project_pk, people_group_pk, by_pk)


@app.task
def notify_project_changes(project_pk: str, changes: Dict[str, Any], by_pk: int):
    """Notify members and followers of a project when it is modified.

    For each change that need to be displayed in the mail, `changes` must
    contain a tuple `(old, new)`.
    E.g. if the title and the description has been changed, `changes` must be:

       {
           'title': ("Old title", "New title")
           'description': ("Old description", "New description")
       }
    """
    return _notify_project_changes(project_pk, changes, by_pk)


@app.task
def notify_new_review(review_id: int):
    """Notify members and followers that a new review has been created."""
    return _notify_new_review(review_id)


@app.task
def notify_ready_for_review(project_pk: int, by_pk: int):
    """Notify reviewers that a project is ready for review."""
    return _notify_ready_for_review(project_pk, by_pk)


@app.task
def notify_new_blogentry(blogentry_pk: int, by_pk: int):
    """Notify members and followers that a new blog entry has been created."""
    return _notify_new_blogentry(blogentry_pk, by_pk)


@app.task
def notify_new_comment(comment_id: int):
    """Notify members and followers that a new comment has been added."""
    return _notify_new_comment(comment_id)


@app.task
def notify_new_announcement(announcement_pk: int, by_pk: int):
    """Notify members and followers that a new announcement has been published."""
    return _notify_new_announcement(announcement_pk, by_pk)


@app.task
def notify_new_application(announcement_pk: int, application: Dict[str, Any]):
    """Notify members of a new application to an announcement."""
    return _notify_new_application(announcement_pk, application)


@app.task
def notify_new_access_request(access_request_pk: int):
    """Notify organization owners of a new access request."""
    return _notify_new_access_request(access_request_pk)


@app.task
def notify_pending_access_requests():
    """Notify organization owners of pending access requests."""
    _notify_pending_access_requests()


@app.task
def send_notifications_reminder():
    users = ProjectUser.objects.filter(notifications_received__to_send=True).distinct()
    _send_notifications_reminder(users)


@app.task
def send_invitations_reminder():
    """
    Send a reminder to org admins about invitation links that are about to expire.
    """
    _send_invitations_reminder()


def notify_new_instructions():
    """Notify members of a new instruction."""
    return _notify_new_instructions()


def _notify_member_added(project_pk: str, user_pk: int, by_pk: int, role: str):
    role = {
        "owners": _("editor"),
        "members": _("participant"),
        "reviewers": _("reviewer"),
    }.get(role)
    project = Project.objects.get(pk=project_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    user = ProjectUser.objects.get(pk=user_pk)
    new_members = [
        {
            "id": user.id,
            "given_name": user.given_name,
            "family_name": user.family_name,
            "role": str(role),
        }
    ]
    for manager in [AddMembersNotificationManager, AddMemberNotificationManager]:
        manager(
            sender, project, new_members=new_members
        ).create_and_send_notifications()


def _notify_group_as_member_added(project_pk: str, group_id: int, by_pk: int):
    project = Project.objects.get(pk=project_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    people_group = PeopleGroup.objects.get(pk=group_id)
    people_group_data = {
        "id": people_group.id,
        "name": people_group.name,
    }
    new_members = [user.id for user in people_group.get_all_members()]
    for manager in [
        AddGroupMembersNotificationManager,
        AddGroupMemberNotificationManager,
    ]:
        manager(
            sender, project, new_members=new_members, group=people_group_data
        ).create_and_send_notifications()


def _notify_member_updated(project_pk: str, user_pk: Set[int], by_pk: int, role: str):
    role = {
        "owners": _("editor"),
        "members": _("participant"),
        "reviewers": _("reviewer"),
    }.get(role)
    project = Project.objects.get(pk=project_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    member = ProjectUser.objects.get(pk=user_pk)
    modified_members = [
        {
            "role": str(role),
            "id": member.id,
            "given_name": member.given_name,
            "family_name": member.family_name,
        }
    ]
    for manager in [UpdateMembersNotificationManager, UpdatedMemberNotificationManager]:
        manager(
            sender, project, modified_members=modified_members
        ).create_and_send_notifications()


def _notify_member_deleted(project_pk: str, user_pk: int, by_pk: int):
    project = Project.objects.get(pk=project_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    user = ProjectUser.objects.get(pk=user_pk)
    deleted_members = [
        {
            "id": user.id,
            "given_name": user.given_name,
            "family_name": user.family_name,
        }
    ]
    manager = DeleteMembersNotificationManager(
        sender, project, deleted_members=deleted_members
    )
    manager.create_and_send_notifications()


def _notify_group_member_deleted(project_pk: str, people_group_pk: int, by_pk: int):
    project = Project.objects.get(pk=project_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    people_group = PeopleGroup.objects.get(pk=people_group_pk)
    deleted_people_groups = [
        {
            "id": people_group.id,
            "name": people_group.name,
        }
    ]
    manager = DeleteGroupMembersNotificationManager(
        sender, project, deleted_people_groups=deleted_people_groups
    )
    manager.create_and_send_notifications()


def _notify_project_changes(project_pk: str, changes: Dict[str, Any], by_pk: int):
    if changes:
        project = Project.objects.get(pk=project_pk)
        sender = ProjectUser.objects.get(pk=by_pk)
        updated_fields = [
            str(Project._meta.get_field(f).verbose_name) for f in list(changes.keys())
        ]
        manager = ProjectEditedNotificationManager(
            sender, project, updated_fields=updated_fields
        )
        manager.create_and_send_notifications()


def _notify_new_review(review_pk: int):
    review = Review.objects.get(pk=review_pk)
    manager = ReviewNotificationManager(review.reviewer, review)
    manager.create_and_send_notifications()


def _notify_ready_for_review(project_pk: int, by_pk: int):
    project = Project.objects.get(pk=project_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    manager = ReadyForReviewNotificationManager(sender, project)
    manager.create_and_send_notifications()


def _notify_new_blogentry(blogentry_pk: int, by_pk: int):
    blogentry = BlogEntry.objects.get(pk=blogentry_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    manager = BlogEntryNotificationManager(sender, blogentry)
    manager.create_and_send_notifications()


def _notify_new_comment(comment_id: int):
    comment = Comment.objects.get(id=comment_id)
    for manager in [
        CommentReplyNotificationManager,
        CommentNotificationManager,
        FollowerCommentNotificationManager,
    ]:
        manager(comment.author, comment).create_and_send_notifications()


def _notify_new_announcement(announcement_pk: int, by_pk: int):
    announcement = Announcement.objects.get(pk=announcement_pk)
    sender = ProjectUser.objects.get(pk=by_pk)
    manager = AnnouncementNotificationManager(sender, announcement)
    manager.create_and_send_notifications()


def _notify_new_application(announcement_pk: int, application: Dict[str, Any]):
    announcement = Announcement.objects.get(pk=announcement_pk)
    manager = ApplicationNotificationManager(
        None, announcement, application=application
    )
    manager.create_and_send_notifications()


def _notify_new_access_request(access_request_pk: int):
    access_request = AccessRequest.objects.get(pk=access_request_pk)
    access_requests = [
        {
            "id": access_request.id,
            "given_name": access_request.given_name,
            "family_name": access_request.family_name,
        }
    ]
    manager = NewAccessRequestNotificationManager(
        None, access_request, access_requests=access_requests
    )
    manager.create_and_send_notifications()


def _notify_pending_access_requests():
    organizations = Organization.objects.all()
    for organization in organizations:
        access_requests = AccessRequest.objects.filter(
            organization=organization, status=AccessRequest.Status.PENDING
        )
        if access_requests.exists():
            manager = PendingAccessRequestsNotificationManager(
                None, organization, requests_count=access_requests.count()
            )
            manager.create_and_send_notifications()


def _send_notifications_reminder(users: dict):
    for user in users:
        notifications = Notification.objects.filter(
            receiver=user, to_send=True
        ).order_by("created")
        for notification in notifications:
            notification.reminder_message = getattr(
                notification, f"reminder_message_{user.language}"
            )
        if len(notifications) > 0:
            subject, _ = render_message("reminder/object", user.language)
            subject = f"\N{sparkles} {subject} \N{sparkles}"
            context = {
                "dateOfTheDay": format_date(date.today(), locale=user.language),
                "notifications": notifications,
                "recipient": user,
            }
            text, html = render_message("reminder/mail", user.language, **context)
            send_email(subject, text, [user.email], html_content=html)
            notifications.update(to_send=False)


def _send_invitations_reminder():
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    expire_today = Invitation.objects.filter(
        expire_at__gte=today, expire_at__lt=today + timedelta(days=1)
    )
    expire_in_seven_days = Invitation.objects.filter(
        expire_at__gte=today + timedelta(days=7),
        expire_at__lt=today + timedelta(days=8),
    )
    for invitation in expire_today:
        manager = InvitationExpiresTodayNotificationManager(
            sender=None, item=invitation
        )
        manager.create_and_send_notifications()
    for invitation in expire_in_seven_days:
        manager = InvitationExpiresInOneWeekNotificationManager(
            sender=None, item=invitation
        )
        manager.create_and_send_notifications()


def _notify_new_instructions():
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    queryset = Instruction.objects.filter(
        notified=False,
        has_to_be_notified=True,
        publication_date__lte=today + timedelta(days=1),
    )
    for instruction in queryset:
        manager = NewInstructionNotificationManager(
            sender=instruction.owner, item=instruction
        )
        manager.create_and_send_notifications()
        instruction.notified = True
        instruction.save()
