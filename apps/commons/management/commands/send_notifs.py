from django.core.management.base import BaseCommand

from apps.accounts.factories import UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.feedbacks.factories import CommentFactory, ReviewFactory
from apps.notifications.tasks import (
    _notify_member_added,
    _notify_member_deleted,
    _notify_member_updated,
    _notify_new_announcement,
    _notify_new_application,
    _notify_new_blogentry,
    _notify_new_comment,
    _notify_new_review,
    _notify_project_changes,
    _notify_ready_for_review,
    _send_notifications_reminder,
)
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--lang", type=str, help="Language used for the emails.")

    def handle(self, *args, **options):
        language = options.get("lang") if options.get("lang") else "en"
        org_1 = OrganizationFactory(name="Learning Planet Institute")
        project = ProjectFactory(organizations=[org_1])
        user = project.get_owners().users.first()

        user.notification_settings.notify_added_to_project = True
        user.notification_settings.announcement_published = True
        user.notification_settings.announcement_has_new_application = True
        user.notification_settings.followed_project_has_been_edited = True
        user.notification_settings.project_has_been_commented = True
        user.notification_settings.project_has_been_edited = True
        user.notification_settings.project_ready_for_review = True
        user.notification_settings.project_has_been_reviewed = True
        user.notification_settings.comment_received_a_response = True
        user.notification_settings.save()
        user.language = language
        user.save()

        # for comment
        comment = CommentFactory(project=project)
        _notify_new_comment(comment.id)

        # for reply
        comment = CommentFactory(project=project, author=user)
        reply = CommentFactory(project=project, reply_on=comment)
        _notify_new_comment(reply.id)

        # for review
        review = ReviewFactory(project=project)
        _notify_new_review(review.id)

        # added to project
        user.notification_settings.notify_added_to_project = True
        user.notification_settings.save()
        _notify_member_added(
            project_pk=project.pk,
            user_pk=user.pk,
            by_pk=UserFactory().pk,
            role="owners",
        )

        # role updated
        _notify_member_updated(
            project_pk=project.pk,
            user_pk=user.pk,
            by_pk=UserFactory().pk,
            role="owners",
        )

        # member removed
        _notify_member_deleted(
            project_pk=project.pk,
            user_pk=user.pk,
            by_pk=UserFactory().pk,
        )

        # for announcement
        reviewer = UserFactory()
        project.reviewers.add(reviewer)
        reviewer.notification_settings.notify_added_to_project = False
        reviewer.notification_settings.announcement_published = False
        reviewer.notification_settings.announcement_has_new_application = False
        reviewer.notification_settings.followed_project_has_been_edited = False
        reviewer.notification_settings.project_has_been_commented = False
        reviewer.notification_settings.project_has_been_edited = False
        reviewer.notification_settings.project_ready_for_review = True
        reviewer.notification_settings.project_has_been_reviewed = False
        reviewer.notification_settings.comment_received_a_response = False
        reviewer.notification_settings.save()
        reviewer.language = language
        reviewer.save()

        announcement = AnnouncementFactory(project=project)
        payload = {
            "project_id": project.id,
            "announcement_id": announcement.id,
            "applicant_name": "Onaisi",
            "applicant_firstname": "Sam",
            "applicant_email": "samonaisi@gmail.com",
            "applicant_message": "I search a job !",
            "recaptcha": "dummy value",
        }
        _notify_new_announcement(announcement.pk, reviewer.pk)
        _notify_new_application(announcement.pk, payload)
        _notify_ready_for_review(project.pk, user.pk)
        _notify_project_changes(
            project.pk, {"title": "", "description": "", "sdgs": ""}, reviewer.pk
        )
        _notify_project_changes(project.pk, {"title": ""}, reviewer.pk)
        _notify_project_changes(project.pk, {"purpose": ""}, reviewer.pk)
        entry = BlogEntryFactory(project=project)
        _notify_new_blogentry(entry.pk, reviewer.pk)

        project_2 = ProjectFactory()
        organization_2 = OrganizationFactory(name="Université de Cergy")
        project_2.organizations.add(organization_2)
        user_2 = project_2.get_owners().users.first()
        user_2.notification_settings.notify_added_to_project = True
        user_2.notification_settings.announcement_published = True
        user_2.notification_settings.announcement_has_new_application = True
        user_2.notification_settings.followed_project_has_been_edited = True
        user_2.notification_settings.project_has_been_commented = True
        user_2.notification_settings.project_has_been_edited = True
        user_2.notification_settings.project_ready_for_review = True
        user_2.notification_settings.project_has_been_reviewed = True
        user_2.notification_settings.comment_received_a_response = True
        user_2.notification_settings.save()
        user_2.language = language
        user_2.save()
        _notify_project_changes(project_2.pk, {"title": ""}, reviewer.pk)
        _notify_project_changes(project_2.pk, {"purpose": ""}, reviewer.pk)
        entry2 = BlogEntryFactory(project=project_2)
        entry3 = BlogEntryFactory(project=project_2)
        _notify_new_blogentry(entry2.pk, reviewer.pk)
        _notify_new_blogentry(entry3.pk, reviewer.pk)

        _send_notifications_reminder(users=[user, user_2, reviewer])
